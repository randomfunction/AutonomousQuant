"""Alpha Vantage data provider — intraday data & technical indicators."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.techindicators import TechIndicators

from backend.config import settings

logger = logging.getLogger(__name__)


class AlphaVantageProvider:
    """Thin wrapper around the ``alpha_vantage`` Python library.

    Free tier: 25 requests / day.  Used sparingly for intraday data and
    technical indicators that yfinance does not provide natively.
    """

    def __init__(self) -> None:
        key = settings.ALPHA_VANTAGE_API_KEY
        if not key:
            logger.warning("ALPHA_VANTAGE_API_KEY not set – provider disabled.")
        self._ts = TimeSeries(key=key, output_format="pandas") if key else None
        self._ti = TechIndicators(key=key, output_format="pandas") if key else None

    # ----- Intraday Price Data -----

    def fetch_intraday(
        self,
        ticker: str,
        interval: str = "15min",
        outputsize: str = "compact",
    ) -> pd.DataFrame:
        """Return intraday OHLCV for *ticker*.

        Parameters
        ----------
        interval:   "1min", "5min", "15min", "30min", "60min"
        outputsize: "compact" (last 100 pts) or "full" (full history)
        """
        if self._ts is None:
            logger.error("Alpha Vantage API key not configured.")
            return pd.DataFrame()
        logger.info("AlphaVantage | Intraday %s  interval=%s", ticker, interval)
        try:
            data, _meta = self._ts.get_intraday(
                symbol=ticker, interval=interval, outputsize=outputsize
            )
            data.columns = ["open", "high", "low", "close", "volume"]
            data.index.name = "datetime"
            return data
        except Exception as exc:
            logger.error("AlphaVantage intraday error: %s", exc)
            return pd.DataFrame()

    # ----- Technical Indicators -----

    def fetch_technical_indicator(
        self,
        ticker: str,
        indicator: str = "SMA",
        time_period: int = 20,
        series_type: str = "close",
        interval: str = "daily",
    ) -> pd.DataFrame:
        """Fetch a technical indicator from Alpha Vantage.

        Supported indicators: SMA, EMA, RSI, MACD, BBANDS, STOCH, ADX, etc.
        """
        if self._ti is None:
            logger.error("Alpha Vantage API key not configured.")
            return pd.DataFrame()
        logger.info("AlphaVantage | %s for %s  period=%d", indicator, ticker, time_period)
        try:
            func = getattr(self._ti, f"get_{indicator.lower()}", None)
            if func is None:
                logger.error("Unsupported indicator: %s", indicator)
                return pd.DataFrame()
            data, _meta = func(
                symbol=ticker,
                interval=interval,
                time_period=time_period,
                series_type=series_type,
            )
            data.index.name = "date"
            return data
        except Exception as exc:
            logger.error("AlphaVantage indicator error: %s", exc)
            return pd.DataFrame()
