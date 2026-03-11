"""FRED (Federal Reserve Economic Data) provider for macro-economic indicators."""

from __future__ import annotations

import logging

import pandas as pd
from fredapi import Fred

from backend.config import settings

logger = logging.getLogger(__name__)

# Common macro series IDs for quick reference
POPULAR_SERIES = {
    "gdp": "GDP",
    "cpi": "CPIAUCSL",
    "fed_funds_rate": "DFF",
    "unemployment": "UNRATE",
    "10y_treasury": "DGS10",
    "2y_treasury": "DGS2",
    "sp500": "SP500",
    "vix": "VIXCLS",
    "m2_money_supply": "M2SL",
    "consumer_sentiment": "UMCSENT",
}


class FredProvider:
    """Fetch macro-economic time-series from the FRED API.

    Free tier: 120 requests / minute — very generous.
    """

    def __init__(self) -> None:
        key = settings.FRED_API_KEY
        if not key:
            logger.warning("FRED_API_KEY not set – provider disabled.")
        self._fred = Fred(api_key=key) if key else None

    def fetch_series(
        self,
        series_id: str,
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        """Return a DataFrame with columns ``[date, value]`` for *series_id*.

        You can use friendly names like ``"gdp"`` or raw IDs like ``"GDP"``.
        """
        # Resolve friendly names
        resolved = POPULAR_SERIES.get(series_id.lower(), series_id)
        if self._fred is None:
            logger.error("FRED API key not configured.")
            return pd.DataFrame()
        logger.info("FRED | Fetching series %s", resolved)
        try:
            data: pd.Series = self._fred.get_series(
                resolved,
                observation_start=start,
                observation_end=end,
            )
            df = data.reset_index()
            df.columns = ["date", "value"]
            return df
        except Exception as exc:
            logger.error("FRED error for %s: %s", resolved, exc)
            return pd.DataFrame()

    def fetch_multiple(
        self,
        series_ids: list[str],
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, pd.DataFrame]:
        """Fetch several series at once."""
        return {sid: self.fetch_series(sid, start, end) for sid in series_ids}

    @staticmethod
    def list_popular() -> dict[str, str]:
        """Return the mapping of friendly-name → FRED series ID."""
        return dict(POPULAR_SERIES)
