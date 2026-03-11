"""FastAPI application — REST + WebSocket server for the Quant Agent."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import settings
from backend.agent.quant_agent import QuantAgent
from backend.agent.tools import get_memory

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
#  Lifespan — initialise singletons
# ──────────────────────────────────────────────────────────────────────

_agent: QuantAgent | None = None
_ws_clients: set[WebSocket] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )
    _agent = QuantAgent()
    logger.info("QuantAgent ready — server starting on %s:%s", settings.HOST, settings.PORT)
    yield
    logger.info("Server shutting down.")


# ──────────────────────────────────────────────────────────────────────
#  App
# ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Autonomous Quant Swarm",
    version="1.0.0",
    description="An autonomous agent that researches markets, writes backtests, and learns from results.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────
#  Request / Response models
# ──────────────────────────────────────────────────────────────────────

class AgentRequest(BaseModel):
    prompt: str
    """Natural language instruction for the agent.
    E.g. 'Analyse AAPL and test a momentum strategy over the past 2 years.'"""


class AgentResponse(BaseModel):
    output: str
    intermediate_steps: list[dict[str, Any]]


class HypothesisOut(BaseModel):
    hypothesis_id: str
    hypothesis: str
    metadata: dict[str, Any]
    results: list[dict[str, Any]]


# ──────────────────────────────────────────────────────────────────────
#  REST endpoints
# ──────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "model": settings.GEMINI_MODEL}


@app.post("/api/agent/run", response_model=AgentResponse)
async def run_agent(req: AgentRequest):
    """Run the agent synchronously and return the full result."""
    if not _agent:
        raise HTTPException(503, "Agent not initialised")
    try:
        result = await asyncio.to_thread(_agent.run, req.prompt)
        return AgentResponse(**result)
    except Exception as exc:
        logger.error("Agent error: %s", exc)
        raise HTTPException(500, str(exc))


@app.get("/api/hypotheses", response_model=list[HypothesisOut])
async def list_hypotheses(limit: int = 50):
    """Return all stored hypotheses and their results."""
    memory = get_memory()
    data = memory.get_all_hypotheses(limit)
    return [HypothesisOut(**h) for h in data]


@app.get("/api/hypotheses/{hyp_id}")
async def get_hypothesis(hyp_id: str):
    """Get a single hypothesis by ID."""
    memory = get_memory()
    all_h = memory.get_all_hypotheses(100)
    for h in all_h:
        if h["hypothesis_id"] == hyp_id:
            return h
    raise HTTPException(404, "Hypothesis not found")


# ──────────────────────────────────────────────────────────────────────
#  WebSocket — real-time reasoning logs
# ──────────────────────────────────────────────────────────────────────

@app.websocket("/ws/logs")
async def websocket_logs(ws: WebSocket):
    """Stream agent reasoning steps in real time.

    Client sends: {"prompt": "Analyse AAPL..."}
    Server streams: {"type": "thought"|"tool_call"|"tool_result"|"final_answer", ...}
    """
    await ws.accept()
    _ws_clients.add(ws)
    logger.info("WebSocket client connected (%d total)", len(_ws_clients))

    try:
        while True:
            # Wait for a prompt from the client
            raw = await ws.receive_text()
            data = json.loads(raw)
            prompt = data.get("prompt", "")

            if not prompt:
                await ws.send_json({"type": "error", "content": "No prompt provided"})
                continue

            if not _agent:
                await ws.send_json({"type": "error", "content": "Agent not ready"})
                continue

            # Stream reasoning steps
            await ws.send_json({
                "type": "status",
                "content": f"Starting research: {prompt[:100]}...",
            })

            async for event in _agent.run_streaming(prompt):
                try:
                    await ws.send_json(event)
                    # Also broadcast to all other connected clients
                    for client in _ws_clients:
                        if client != ws:
                            try:
                                await client.send_json(event)
                            except Exception:
                                pass
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
    finally:
        _ws_clients.discard(ws)


# ──────────────────────────────────────────────────────────────────────
#  Entry-point for running directly
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
