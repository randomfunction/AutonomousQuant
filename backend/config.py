"""Central configuration loaded from environment variables / .env file."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


class Settings:
    """Application settings sourced from environment."""

    # --- LLM ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")

    # --- Data Providers ---
    ALPHA_VANTAGE_API_KEY: str = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    FRED_API_KEY: str = os.getenv("FRED_API_KEY", "")

    # --- Backtester ---
    BACKTEST_TIMEOUT_SECONDS: int = int(os.getenv("BACKTEST_TIMEOUT_SECONDS", "60"))
    BACKTEST_INITIAL_CASH: float = float(os.getenv("BACKTEST_INITIAL_CASH", "100000"))

    # --- Vector Store (FAISS) ---
    VECTOR_STORE_DIR: str = os.getenv(
        "VECTOR_STORE_DIR",
        str(Path(__file__).resolve().parent.parent / "data" / "vector_store"),
    )

    # --- Server ---
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")


settings = Settings()
