# Autonomous Quantitative Research & Backtesting Swarm

An autonomous AI agent that researches financial markets, formulates trading hypotheses, writes and executes backtesting code, and learns from results — all surfaced through a real-time React dashboard.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│   React/TypeScript Dashboard (Vite)                 │
│   ├── Reasoning Log (WebSocket live feed)           │
│   ├── Code Viewer (syntax-highlighted Python)       │
│   ├── Equity Curves (Recharts)                      │
│   └── Hypothesis History (auto-refresh table)       │
├─────────────────────────────────────────────────────┤
│   FastAPI Server (REST + WebSocket)                 │
│   ├── LangChain Agent (Gemini 2.0 Flash)            │
│   ├── Data Providers (yfinance, Alpha Vantage, FRED)│
│   ├── Backtest Engine (backtrader, sandboxed)       │
│   └── Vector Memory (ChromaDB, local)               │
└─────────────────────────────────────────────────────┘
```

## Quick Start

### 1. API Keys (all free, no credit card)

Copy the env template and fill in your keys:

```bash
cp .env.example .env
```

| Key | Get it from |
|-----|-------------|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) |
| `ALPHA_VANTAGE_API_KEY` | [alphavantage.co](https://www.alphavantage.co/support/#api-key) |
| `FRED_API_KEY` | [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html) |

> `yfinance` and `ChromaDB` need **no keys** at all.

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Start the server
python -m backend.main
```

Server runs at `http://localhost:8000` with docs at `/docs`.

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Dashboard runs at `http://localhost:5173`.

## Usage

1. Open the dashboard at `http://localhost:5173`
2. Type a research prompt, e.g.:
   - *"Analyse AAPL and test a SMA crossover strategy over the past 2 years"*
   - *"Research BTC-USD and test a momentum-based strategy"*
3. Watch the agent reason in real-time in the Reasoning Log
4. View generated backtrader code in the Code Viewer
5. See equity curves and performance metrics after backtest runs
6. Check the History tab for all past hypotheses and outcomes

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Gemini 2.0 Flash (via LangChain) |
| Agent Framework | LangChain + Tool Calling |
| Market Data | yfinance (free), Alpha Vantage (free), FRED (free) |
| Backtesting | backtrader (sandboxed subprocess) |
| Memory | ChromaDB (local vector database) |
| Backend | FastAPI + WebSockets |
| Frontend | React + TypeScript + Vite |
| Charts | Recharts |
| Code Highlighting | react-syntax-highlighter |

## Project Structure

```
AutonomousQuant/
├── backend/
│   ├── main.py                       # FastAPI server
│   ├── config.py                     # Environment config
│   ├── agent/
│   │   ├── quant_agent.py            # LangChain agent
│   │   ├── prompts.py                # System prompts
│   │   └── tools.py                  # Tool definitions
│   ├── backtester/
│   │   ├── engine.py                 # Sandboxed executor
│   │   └── templates.py              # Strategy templates
│   ├── data_providers/
│   │   ├── yfinance_provider.py      # Yahoo Finance
│   │   ├── alpha_vantage_provider.py # Alpha Vantage
│   │   └── fred_provider.py          # FRED economic data
│   └── memory/
│       └── vector_store.py           # ChromaDB wrapper
├── frontend/
│   └── src/
│       ├── App.tsx                   # Main layout
│       ├── App.css                   # Dark theme styles
│       ├── components/
│       │   ├── ReasoningLog.tsx       # Live reasoning feed
│       │   ├── CodeViewer.tsx         # Python code viewer
│       │   ├── EquityCurve.tsx        # Charts + metrics
│       │   └── HypothesisHistory.tsx  # Past results table
│       ├── hooks/useWebSocket.ts     # WS connection hook
│       └── api/client.ts            # REST API client
├── .env.example
├── requirements.txt
└── README.md
```
