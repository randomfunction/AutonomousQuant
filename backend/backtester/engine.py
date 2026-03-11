"""Sandboxed backtest execution engine.

Receives a Python string (backtrader strategy), writes it to a temp file,
and executes it in a subprocess with timeout and restricted imports.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from backend.config import settings

logger = logging.getLogger(__name__)

# Imports that are BLOCKED in generated strategies for security
BLOCKED_IMPORTS = [
    "os", "sys", "subprocess", "shutil", "socket", "http",
    "requests", "urllib", "pathlib", "glob", "importlib",
    "ctypes", "multiprocessing", "threading", "signal",
]

BLOCKED_PATTERN = re.compile(
    r"(?:^|\s)(?:import|from)\s+(" + "|".join(BLOCKED_IMPORTS) + r")\b",
    re.MULTILINE,
)


class BacktestEngine:
    """Execute agent-generated backtest code safely."""

    def __init__(self) -> None:
        self._tmp_dir = Path(tempfile.mkdtemp(prefix="quant_bt_"))
        self._data_dir = Path(settings.VECTOR_STORE_DIR).parent / "backtest_data"
        self._data_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    #  Public API                                                        #
    # ------------------------------------------------------------------ #

    def prepare_data(self, df: pd.DataFrame, filename: str = "data.csv") -> str:
        """Write a DataFrame to CSV for backtrader to consume. Returns the path."""
        csv_path = str(self._data_dir / filename)
        # backtrader expects: datetime, open, high, low, close, volume
        cols = ["open", "high", "low", "close", "volume"]
        export = df[[c for c in cols if c in df.columns]].copy()
        export.index.name = "datetime"
        export.to_csv(csv_path)
        logger.info("Backtest data saved → %s  (%d rows)", csv_path, len(export))
        return csv_path

    def validate_code(self, code: str) -> tuple[bool, str]:
        """Check generated code for disallowed imports. Returns (ok, reason)."""
        match = BLOCKED_PATTERN.search(code)
        if match:
            return False, f"Blocked import detected: {match.group(1)}"
        # Check for exec/eval
        if re.search(r"\b(exec|eval|compile|__import__)\s*\(", code):
            return False, "Blocked function call: exec/eval/compile/__import__"
        return True, "OK"

    def execute(
        self,
        code: str,
        data_csv_path: str,
        initial_cash: float | None = None,
    ) -> dict[str, Any]:
        """Run the backtest in a subprocess and return structured results.

        Returns
        -------
        dict with keys: success, metrics (if success), error (if failure),
        code (the strategy code), stdout, equity_curve.
        """
        # Validate first
        ok, reason = self.validate_code(code)
        if not ok:
            return {"success": False, "error": reason, "code": code, "metrics": {}}

        cash = initial_cash or settings.BACKTEST_INITIAL_CASH

        # Write code to temp file
        script_path = self._tmp_dir / f"strategy_{os.getpid()}.py"
        script_path.write_text(code, encoding="utf-8")

        try:
            result = subprocess.run(
                [sys.executable, str(script_path), data_csv_path, str(cash)],
                capture_output=True,
                text=True,
                timeout=settings.BACKTEST_TIMEOUT_SECONDS,
                cwd=str(self._tmp_dir),
            )

            stdout = result.stdout
            stderr = result.stderr

            if result.returncode != 0:
                logger.error("Backtest failed:\n%s", stderr)
                return {
                    "success": False,
                    "error": stderr[-2000:] if len(stderr) > 2000 else stderr,
                    "code": code,
                    "metrics": {},
                    "stdout": stdout,
                }

            # Parse structured output
            metrics = self._parse_results(stdout)
            return {
                "success": True,
                "metrics": metrics,
                "code": code,
                "stdout": stdout,
                "error": None,
            }

        except subprocess.TimeoutExpired:
            logger.error("Backtest timed out after %ds", settings.BACKTEST_TIMEOUT_SECONDS)
            return {
                "success": False,
                "error": f"Timeout: script exceeded {settings.BACKTEST_TIMEOUT_SECONDS}s",
                "code": code,
                "metrics": {},
            }
        except Exception as exc:
            logger.error("Backtest execution error: %s", exc)
            return {
                "success": False,
                "error": str(exc),
                "code": code,
                "metrics": {},
            }

    # ------------------------------------------------------------------ #
    #  Parsing                                                           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_results(stdout: str) -> dict[str, Any]:
        """Extract the JSON block between ===BACKTEST_RESULT=== markers."""
        marker_start = "===BACKTEST_RESULT==="
        marker_end = "===END_RESULT==="
        try:
            start = stdout.index(marker_start) + len(marker_start)
            end = stdout.index(marker_end)
            raw = stdout[start:end].strip()
            return json.loads(raw)
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("Could not parse backtest results: %s", exc)
            return {}
