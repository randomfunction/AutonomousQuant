"""LangChain tool definitions for the Quant Agent.

Each tool wraps a backend component (data providers, backtester, memory)
and exposes it to the LLM via function-calling.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import tool

from backend.data_providers.yfinance_provider import YFinanceProvider
from backend.data_providers.alpha_vantage_provider import AlphaVantageProvider
from backend.data_providers.fred_provider import FredProvider
from backend.backtester.engine import BacktestEngine
from backend.memory.vector_store import VectorStore

logger = logging.getLogger(__name__)

# Shared singleton instances (initialised once, reused across tool calls)
_yf = YFinanceProvider()
_av = AlphaVantageProvider()
_fred = FredProvider()
_engine = BacktestEngine()
_memory = VectorStore()


def get_memory() -> VectorStore:
    """Expose the memory store for external access (e.g., API routes)."""
    return _memory


# ──────────────────────────────────────────────────────────────────────
#  Data tools
# ──────────────────────────────────────────────────────────────────────

@tool
def fetch_market_data(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> str:
    """Fetch historical OHLCV data for a ticker using Yahoo Finance.

    Args:
        ticker: Stock/ETF/crypto symbol, e.g. "AAPL", "BTC-USD", "EURUSD=X"
        period: Time period — "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"
        interval: Bar interval — "1d", "1wk", "1mo"

    Returns:
        A summary of the data with basic statistics and recent prices.
    """
    df = _yf.fetch_historical(ticker, period, interval)
    if df.empty:
        return f"No data found for {ticker}"

    # Save CSV for later backtest use
    csv_path = _engine.prepare_data(df, f"{ticker.replace('/', '_')}_{period}.csv")

    summary = {
        "ticker": ticker,
        "period": period,
        "interval": interval,
        "rows": len(df),
        "date_range": f"{df.index[0]} → {df.index[-1]}",
        "latest_close": round(float(df["close"].iloc[-1]), 2),
        "high_52w": round(float(df["close"].max()), 2),
        "low_52w": round(float(df["close"].min()), 2),
        "mean_close": round(float(df["close"].mean()), 2),
        "std_close": round(float(df["close"].std()), 2),
        "mean_volume": int(df["volume"].mean()) if "volume" in df.columns else 0,
        "return_total": round(
            float((df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100), 2
        ),
        "csv_path": csv_path,
    }
    return json.dumps(summary, indent=2, default=str)


@tool
def fetch_fundamentals(ticker: str) -> str:
    """Fetch fundamental financial data for a ticker (PE, market cap, sector, etc.)

    Args:
        ticker: Stock symbol, e.g. "AAPL", "MSFT"

    Returns:
        JSON string of key fundamental metrics.
    """
    data = _yf.fetch_fundamentals(ticker)
    return json.dumps(data, indent=2, default=str)


@tool
def fetch_macro_data(
    series_id: str,
    start: str = "",
    end: str = "",
) -> str:
    """Fetch macro-economic data from FRED.

    Popular series IDs: gdp, cpi, fed_funds_rate, unemployment,
    10y_treasury, 2y_treasury, vix, consumer_sentiment

    Args:
        series_id: FRED series ID or friendly name
        start: Optional start date (YYYY-MM-DD)
        end: Optional end date (YYYY-MM-DD)

    Returns:
        Summary of the economic series with recent values.
    """
    df = _fred.fetch_series(
        series_id,
        start=start or None,
        end=end or None,
    )
    if df.empty:
        return f"No FRED data for series '{series_id}'. Is your FRED_API_KEY set?"

    recent = df.tail(5).to_dict("records")
    summary = {
        "series_id": series_id,
        "rows": len(df),
        "latest_value": recent[-1] if recent else None,
        "recent_values": recent,
    }
    return json.dumps(summary, indent=2, default=str)


@tool
def fetch_technical_indicators(
    ticker: str,
    indicator: str = "SMA",
    time_period: int = 20,
) -> str:
    """Fetch a technical indicator from Alpha Vantage.

    Supported: SMA, EMA, RSI, MACD, BBANDS, STOCH, ADX

    Args:
        ticker: Stock symbol, e.g. "AAPL"
        indicator: Indicator name (SMA, EMA, RSI, MACD, etc.)
        time_period: Look-back period for the indicator

    Returns:
        Recent indicator values as JSON.
    """
    df = _av.fetch_technical_indicator(ticker, indicator, time_period)
    if df.empty:
        return f"Could not fetch {indicator} for {ticker}. Alpha Vantage may be rate-limited."
    recent = df.head(10)
    return recent.to_json(indent=2, default_handler=str)


# ──────────────────────────────────────────────────────────────────────
#  Backtest tools
# ──────────────────────────────────────────────────────────────────────

@tool
def write_and_execute_backtest(
    code: str,
    data_csv_path: str,
    initial_cash: float = 100000.0,
) -> str:
    """Write a backtrader strategy and execute it in a sandboxed environment.

    The code MUST define a GeneratedStrategy(bt.Strategy) class and a
    run_backtest() function that prints results between ===BACKTEST_RESULT===
    and ===END_RESULT=== markers.

    Args:
        code: Complete Python backtrader script
        data_csv_path: Path to the CSV data file (returned by fetch_market_data)
        initial_cash: Starting portfolio value (default 100000)

    Returns:
        JSON with success status, metrics, and any errors.
    """
    result = _engine.execute(code, data_csv_path, initial_cash)
    return json.dumps(result, indent=2, default=str)


# ──────────────────────────────────────────────────────────────────────
#  Memory tools
# ──────────────────────────────────────────────────────────────────────

@tool
def search_memory(query: str, n: int = 5) -> str:
    """Search past hypotheses and their results for similar strategies.

    Use this BEFORE writing a new backtest to learn from past attempts.

    Args:
        query: Description of the strategy or hypothesis to search for
        n: Number of similar results to return (default 5)

    Returns:
        JSON list of similar past hypotheses with their backtest outcomes.
    """
    results = _memory.search_similar(query, n)
    if not results:
        return "No similar hypotheses found in memory yet."
    return json.dumps(results, indent=2, default=str)


@tool
def store_hypothesis_and_result(
    hypothesis: str,
    ticker: str,
    strategy_type: str,
    metrics: str,
) -> str:
    """Store a hypothesis and its backtest result in long-term memory.

    Call this AFTER every backtest to build the knowledge base.

    Args:
        hypothesis: Full text of the trading hypothesis
        ticker: The ticker(s) tested
        strategy_type: E.g. "SMA Crossover", "RSI Mean Reversion"
        metrics: JSON string of backtest metrics (total_return, sharpe_ratio, etc.)

    Returns:
        Confirmation with the hypothesis ID.
    """
    try:
        metrics_dict = json.loads(metrics) if isinstance(metrics, str) else metrics
    except json.JSONDecodeError:
        metrics_dict = {"raw": metrics}

    hyp_id = _memory.store_hypothesis(
        text=hypothesis,
        metadata={"ticker": ticker, "strategy_type": strategy_type},
    )

    total_return = metrics_dict.get("total_return", 0)
    _memory.store_result(
        hypothesis_id=hyp_id,
        metrics={
            "total_return": total_return,
            "sharpe_ratio": metrics_dict.get("sharpe_ratio"),
            "max_drawdown": metrics_dict.get("max_drawdown"),
            "total_trades": metrics_dict.get("total_trades"),
            "success": total_return > 0,
        },
        summary=f"{strategy_type} on {ticker}: {total_return}% return",
    )

    return json.dumps({"stored": True, "hypothesis_id": hyp_id})


@tool
def get_failed_strategies(n: int = 5) -> str:
    """Retrieve past strategies that resulted in negative returns.

    Use this to avoid repeating mistakes.

    Args:
        n: Number of failed strategies to return

    Returns:
        JSON list of failed hypotheses with their negative results.
    """
    failures = _memory.get_failed_patterns(n)
    if not failures:
        return "No failed strategies in memory yet."
    return json.dumps(failures, indent=2, default=str)


# ──────────────────────────────────────────────────────────────────────
#  Full tool list for the agent
# ──────────────────────────────────────────────────────────────────────

ALL_TOOLS = [
    fetch_market_data,
    fetch_fundamentals,
    fetch_macro_data,
    fetch_technical_indicators,
    write_and_execute_backtest,
    search_memory,
    store_hypothesis_and_result,
    get_failed_strategies,
]
