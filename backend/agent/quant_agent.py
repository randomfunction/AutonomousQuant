"""Core Quantitative Research Agent — LangChain + Gemini 2.0 Flash.

Implements a ReAct-style agent that can research markets, formulate hypotheses,
write backtests, execute them, and learn from results.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.callbacks import BaseCallbackHandler

from backend.config import settings
from backend.agent.prompts import SYSTEM_PROMPT
from backend.agent.tools import ALL_TOOLS

logger = logging.getLogger(__name__)


class StreamingCallbackHandler(BaseCallbackHandler):
    """Captures agent reasoning steps and pushes them to an async queue."""

    def __init__(self, queue: asyncio.Queue) -> None:
        self.queue = queue
        self._loop: asyncio.AbstractEventLoop | None = None

    def _put(self, data: dict) -> None:
        """Thread-safe put into the asyncio queue."""
        try:
            loop = self._loop or asyncio.get_event_loop()
            loop.call_soon_threadsafe(self.queue.put_nowait, data)
        except Exception:
            pass

    def on_llm_start(self, serialized: dict, prompts: list[str], **kwargs: Any) -> None:
        self._put({
            "type": "thinking",
            "content": "Reasoning...",
            "timestamp": _now(),
        })

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        try:
            text = response.generations[0][0].text if response.generations else ""
            if text:
                self._put({
                    "type": "thought",
                    "content": text[:3000],
                    "timestamp": _now(),
                })
        except Exception:
            pass

    def on_tool_start(
        self, serialized: dict, input_str: str, **kwargs: Any
    ) -> None:
        tool_name = serialized.get("name", "unknown_tool")
        self._put({
            "type": "tool_call",
            "tool": tool_name,
            "input": input_str[:1000],
            "timestamp": _now(),
        })

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        self._put({
            "type": "tool_result",
            "content": output[:2000],
            "timestamp": _now(),
        })

    def on_agent_action(self, action: Any, **kwargs: Any) -> None:
        self._put({
            "type": "action",
            "tool": getattr(action, "tool", "?"),
            "input": str(getattr(action, "tool_input", ""))[:1000],
            "timestamp": _now(),
        })

    def on_agent_finish(self, finish: Any, **kwargs: Any) -> None:
        self._put({
            "type": "final_answer",
            "content": str(finish.return_values.get("output", ""))[:3000],
            "timestamp": _now(),
        })
        self._put({"type": "done"})


class QuantAgent:
    """Autonomous Quantitative Research Agent."""

    def __init__(self) -> None:
        self._llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.2,
            convert_system_message_to_human=True,
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(self._llm, ALL_TOOLS, prompt)
        self._executor = AgentExecutor(
            agent=agent,
            tools=ALL_TOOLS,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=15,
            return_intermediate_steps=True,
        )

        self._chat_history: list = []
        logger.info("QuantAgent initialised with model=%s", settings.GEMINI_MODEL)

    # ------------------------------------------------------------------ #
    #  Synchronous run (for simple API calls)                             #
    # ------------------------------------------------------------------ #

    def run(self, user_input: str) -> dict[str, Any]:
        """Run the agent synchronously and return the final result."""
        result = self._executor.invoke({
            "input": user_input,
            "chat_history": self._chat_history,
        })
        # Update chat history
        self._chat_history.append(HumanMessage(content=user_input))
        self._chat_history.append(
            AIMessage(content=result.get("output", ""))
        )
        # Trim history to last 20 messages
        if len(self._chat_history) > 20:
            self._chat_history = self._chat_history[-20:]

        return {
            "output": result.get("output", ""),
            "intermediate_steps": _serialize_steps(
                result.get("intermediate_steps", [])
            ),
        }

    # ------------------------------------------------------------------ #
    #  Streaming run (for WebSocket real-time updates)                    #
    # ------------------------------------------------------------------ #

    async def run_streaming(
        self, user_input: str
    ) -> AsyncGenerator[dict, None]:
        """Run the agent and yield reasoning steps as they happen."""
        queue: asyncio.Queue = asyncio.Queue()
        handler = StreamingCallbackHandler(queue)
        handler._loop = asyncio.get_event_loop()

        # Run executor in a thread to avoid blocking the event loop
        async def _invoke() -> dict:
            return await asyncio.to_thread(
                self._executor.invoke,
                {
                    "input": user_input,
                    "chat_history": self._chat_history,
                },
                {"callbacks": [handler]},
            )

        task = asyncio.create_task(_invoke())

        # Yield events as they arrive
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=120)
                yield event
                if event.get("type") == "done":
                    break
            except asyncio.TimeoutError:
                yield {"type": "error", "content": "Agent timed out", "timestamp": _now()}
                break
            except Exception as exc:
                yield {"type": "error", "content": str(exc), "timestamp": _now()}
                break

        # Collect final result
        try:
            result = await task
            self._chat_history.append(HumanMessage(content=user_input))
            self._chat_history.append(
                AIMessage(content=result.get("output", ""))
            )
            if len(self._chat_history) > 20:
                self._chat_history = self._chat_history[-20:]
        except Exception as exc:
            logger.error("Agent execution error: %s", exc)
            yield {"type": "error", "content": str(exc), "timestamp": _now()}


# ──────────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize_steps(steps: list) -> list[dict]:
    """Convert LangChain intermediate steps to JSON-friendly dicts."""
    serialized = []
    for action, observation in steps:
        serialized.append({
            "tool": getattr(action, "tool", "unknown"),
            "input": str(getattr(action, "tool_input", "")),
            "output": str(observation)[:2000],
        })
    return serialized
