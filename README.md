<p align="center">
  <h1 align="center">Autonomous Quant Swarm</h1>
  <p align="center">
    <strong>An AI-powered quantitative research agent that autonomously researches markets, formulates trading hypotheses, writes & executes backtests, and learns from results.</strong>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black" alt="React" />
    <img src="https://img.shields.io/badge/TypeScript-5.9-3178C6?logo=typescript&logoColor=white" alt="TypeScript" />
    <img src="https://img.shields.io/badge/Gemini_2.0_Flash-4285F4?logo=google&logoColor=white" alt="Gemini" />
    <img src="https://img.shields.io/badge/LangChain-🦜-1C3C3C" alt="LangChain" />
  </p>
</p>

---

## What Is This?

Autonomous Quant Swarm is a full-stack application that puts a **ReAct-style AI agent** at the helm of quantitative research. You give it a natural-language prompt — like *"Analyse AAPL and test a momentum strategy over the past 2 years"* — and the agent autonomously:

1. **Fetches real market data** from Yahoo Finance, Alpha Vantage, and FRED
2. **Analyses** price trends, fundamentals, and macro-economic context
3. **Formulates** a testable trading hypothesis
4. **Checks memory** for similar past strategies to avoid repeating failures
5. **Writes** a complete [Backtrader](https://www.backtrader.com/) strategy in Python
6. **Executes** the backtest in a sandboxed environment
7. **Evaluates** the results (Sharpe ratio, max drawdown, total return, win rate)
8. **Stores** every result in vector memory and **iterates** to improve

All reasoning steps are **streamed in real time** to a sleek React dashboard via WebSocket.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    React / Vite Frontend                  │
│  ┌──────────┐ ┌───────────┐ ┌────────────┐ ┌──────────┐ │
│  │Reasoning │ │  Code     │ │  Equity    │ │Hypothesis│ │
│  │  Log     │ │  Viewer   │ │  Curve     │ │ History  │ │
│  └──────────┘ └───────────┘ └────────────┘ └──────────┘ │
└────────────────────────┬─────────────────────────────────┘
                         │  WebSocket + REST
┌────────────────────────▼─────────────────────────────────┐
│                  FastAPI Backend Server                    │
│  ┌───────────────────────────────────────────────────┐   │
│  │            LangChain ReAct Agent (Gemini 2.0)     │   │
│  │  ┌──────────┐ ┌───────────┐ ┌──────────────────┐ │   │
│  │  │  Data    │ │ Backtest  │ │  Vector Memory   │ │   │
│  │  │  Tools   │ │  Engine   │ │  (FAISS)         │ │   │
│  │  └──────────┘ └───────────┘ └──────────────────┘ │   │
│  └───────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
     │                    │                    │
     ▼                    ▼                    ▼
 Yahoo Finance      Alpha Vantage          FRED API
```

---

## Features

| Feature | Description |
|---|---|
| **Autonomous Agent** | ReAct-style agent loop: Analyse → Hypothesise → Backtest → Evaluate → Iterate |
| **Multi-Source Data** | Yahoo Finance (OHLCV, fundamentals), Alpha Vantage (technicals), FRED (macro) |
| **Automated Backtesting** | Generates and executes full Backtrader strategies in a sandboxed subprocess |
| **Vector Memory** | FAISS-powered long-term memory — learns from past successes and failures |
| **Real-Time Streaming** | WebSocket-based live streaming of every reasoning step, tool call, and result |
| **Interactive Dashboard** | React UI with reasoning log, code viewer, equity curves, and hypothesis history |
| **Chat Interface** | Natural language input — just describe what you want to research |

---

## Getting Started

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** and **npm**
- API keys for:
  - [Google Gemini](https://ai.google.dev/) (required)
  - [Alpha Vantage](https://www.alphavantage.co/support/#api-key) (optional — for technical indicators)
  - [FRED](https://fred.stlouisfed.org/docs/api/api_key.html) (optional — for macro data)

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/AutonomousQuant.git
cd AutonomousQuant
```

### 2. Backend Setup

```bash
# Create and activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash

# Optional
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
FRED_API_KEY=your_fred_key
```

### 4. Frontend Setup

```bash
cd frontend
npm install
```

### 5. Run the Application

**Terminal 1 — Start the backend:**
```bash
# From project root
python main.py
```
The API server starts at `http://localhost:8000`.

**Terminal 2 — Start the frontend:**
```bash
cd frontend
npm run dev
```
The dashboard opens at `http://localhost:5173`.

---

## API Reference

### REST Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check — returns status and model name |
| `POST` | `/api/agent/run` | Run the agent synchronously with a prompt |
| `GET` | `/api/hypotheses` | List all stored hypotheses and results |
| `GET` | `/api/hypotheses/{id}` | Get a single hypothesis by ID |

### WebSocket

| Endpoint | Description |
|---|---|
| `ws://localhost:8000/ws/logs` | Send `{"prompt": "..."}` and receive real-time reasoning events |

**Event types streamed:** `thinking`, `thought`, `tool_call`, `tool_result`, `action`, `final_answer`, `status`, `error`, `done`

---

## Agent Tools

The agent has access to the following tools via LangChain function-calling:

| Tool | Description |
|---|---|
| `fetch_market_data` | Historical OHLCV data from Yahoo Finance |
| `fetch_fundamentals` | PE ratio, market cap, sector, and other fundamentals |
| `fetch_technical_indicators` | SMA, EMA, RSI, MACD, BBANDS, STOCH, ADX from Alpha Vantage |
| `fetch_macro_data` | GDP, CPI, Fed Funds Rate, unemployment, etc. from FRED |
| `write_and_execute_backtest` | Generate and run a Backtrader strategy in a sandbox |
| `search_memory` | Search past hypotheses for similar strategies |
| `store_hypothesis_and_result` | Save a hypothesis and its backtest result to memory |
| `get_failed_strategies` | Retrieve strategies that had negative returns |

---

## Project Structure

```
AutonomousQuant/
├── main.py                          # FastAPI app entry point (REST + WebSocket)
├── requirements.txt                 # Python dependencies
├── .env                             # Environment variables (not committed)
│
├── backend/
│   ├── config.py                    # Central settings from environment
│   ├── agent/
│   │   ├── quant_agent.py           # Core ReAct agent (LangChain + Gemini)
│   │   ├── tools.py                 # LangChain tool definitions
│   │   └── prompts.py              # System prompts and templates
│   ├── backtester/
│   │   ├── engine.py                # Sandboxed Backtrader execution engine
│   │   └── templates.py            # Strategy code templates
│   ├── data_providers/
│   │   ├── yfinance_provider.py     # Yahoo Finance data fetcher
│   │   ├── alpha_vantage_provider.py# Alpha Vantage technical indicators
│   │   └── fred_provider.py        # FRED macro-economic data
│   └── memory/
│       └── vector_store.py          # FAISS vector store for hypothesis memory
│
├── frontend/                        # React + Vite + TypeScript UI
│   ├── src/
│   │   ├── App.tsx                  # Main application shell
│   │   ├── components/
│   │   │   ├── ReasoningLog.tsx     # Live agent reasoning stream
│   │   │   ├── CodeViewer.tsx       # Syntax-highlighted strategy code
│   │   │   ├── EquityCurve.tsx      # Portfolio performance charts
│   │   │   └── HypothesisHistory.tsx# Past hypotheses browser
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts      # WebSocket connection hook
│   │   └── api/                     # REST API client
│   └── package.json
│
└── data/                            # Runtime data (CSV cache, vector store)
```

---

## Example Prompts

Try these with the agent:

- *"Analyse AAPL and test a SMA crossover strategy over the past 2 years"*
- *"Research BTC-USD and test a momentum-based strategy"*
- *"Compare RSI mean reversion vs trend following on MSFT"*
- *"Test a dual moving average strategy on SPY with optimized periods"*
- *"Fetch macro data for Fed Funds Rate and check how it correlates with S&P 500 performance"*

---

## Tech Stack

| Layer | Technology |
|---|---|
| **LLM** | Google Gemini 2.0 Flash |
| **Agent Framework** | LangChain (ReAct tool-calling agent) |
| **Backend** | FastAPI + Uvicorn |
| **Backtesting** | Backtrader |
| **Vector Memory** | FAISS + Sentence Transformers |
| **Market Data** | Yahoo Finance, Alpha Vantage, FRED |
| **Frontend** | React 19 + TypeScript + Vite |
| **Charts** | Recharts |
| **Code Display** | react-syntax-highlighter |

---

## License

This project is open source and available under the [MIT License](LICENSE).

---

<p align="center">
  Built with ⚡ by Autonomous Quant Swarm
</p>
