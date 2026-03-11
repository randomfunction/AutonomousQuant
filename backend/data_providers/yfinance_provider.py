"""Yahoo Finance data provider using the yfinance library (no API key needed)."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


class YFinanceProvider:
    """Fetches historical OHLCV data and fundamentals from Yahoo Finance."""

    # ----- Historical Price Data -----

    @staticmethod
    def fetch_historical(
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """Return OHLCV DataFrame for *ticker*.

        Parameters
        ----------
        ticker:   e.g. "AAPL", "BTC-USD", "EURUSD=X"
        period:   yfinance period string — "1mo", "3mo", "1y", "5y", "max"
        interval: "1d", "1wk", "1mo", "1h" (intraday limited to 730 days)
        """
        logger.info("yfinance | Fetching %s  period=%s  interval=%s", ticker, period, interval)
        tk = yf.Ticker(ticker)
        df: pd.DataFrame = tk.history(period=period, interval=interval)
        if df.empty:
            logger.warning("yfinance | No data returned for %s", ticker)
            return pd.DataFrame()
        # Normalize column names
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        df.index.name = "date"
        return df

    # ----- Fundamentals -----

    @staticmethod
    def fetch_fundamentals(ticker: str) -> dict[str, Any]:
        """Return a flat dict of key fundamental metrics."""
        logger.info("yfinance | Fetching fundamentals for %s", ticker)
        tk = yf.Ticker(ticker)
        info: dict = tk.info or {}
        keys = [
            "shortName", "sector", "industry", "marketCap",
            "trailingPE", "forwardPE", "priceToBook", "dividendYield",
            "returnOnEquity", "debtToEquity", "totalRevenue",
            "revenueGrowth", "earningsGrowth", "fiftyTwoWeekHigh",
            "fiftyTwoWeekLow", "fiftyDayAverage", "twoHundredDayAverage",
            "beta",
        ]
        return {k: info.get(k) for k in keys}

    # ----- Multi-ticker -----

    @staticmethod
    def fetch_multiple(
        tickers: list[str],
        period: str = "1y",
        interval: str = "1d",
    ) -> dict[str, pd.DataFrame]:
        """Fetch OHLCV for several tickers and return {ticker: DataFrame}."""
        result: dict[str, pd.DataFrame] = {}
        for t in tickers:
            result[t] = YFinanceProvider.fetch_historical(t, period, interval)
        return result
