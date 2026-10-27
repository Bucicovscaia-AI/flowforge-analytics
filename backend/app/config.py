"""Application settings, read from environment variables.

Secrets (the AI API key, the Make.com webhook URL and its API key) are never
written in the code. They are loaded from a local .env file that is excluded
from Git, or from the hosting platform's environment settings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

APP_VERSION = "1.0.0"
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    max_upload_mb: int
    max_rows: int
    max_columns: int
    frontend_origin: str
    data_dir: Path
    sample_data_dir: Path
    static_dir: Path
    ai_api_key: str
    ai_model: str
    ai_timeout_seconds: int
    make_webhook_url: str
    make_webhook_api_key: str
    make_timeout_seconds: int

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def ai_configured(self) -> bool:
        return bool(self.ai_api_key)

    @property
    def webhook_configured(self) -> bool:
        return bool(self.make_webhook_url)


def load_settings() -> Settings:
    """Read settings fresh from the environment (tests override them)."""
    return Settings(
        max_upload_mb=_int("MAX_UPLOAD_MB", 5),
        max_rows=_int("MAX_ROWS", 100_000),
        max_columns=_int("MAX_COLUMNS", 50),
        frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"),
        data_dir=Path(os.getenv("DATA_DIR", str(BACKEND_DIR / "data"))),
        sample_data_dir=Path(os.getenv("SAMPLE_DATA_DIR", str(REPO_DIR / "sample-data"))),
        static_dir=Path(os.getenv("STATIC_DIR", str(REPO_DIR / "frontend" / "dist"))),
        # AI_API_KEY is the project's own name; ANTHROPIC_API_KEY is accepted
        # too because it is the SDK's conventional variable.
        ai_api_key=os.getenv("AI_API_KEY") or os.getenv("ANTHROPIC_API_KEY", ""),
        ai_model=os.getenv("AI_MODEL", "claude-opus-5-5"),
        ai_timeout_seconds=_int("AI_TIMEOUT_SECONDS", 60),
        make_webhook_url=os.getenv("MAKE_WEBHOOK_URL", "").strip(),
        make_webhook_api_key=os.getenv("MAKE_WEBHOOK_API_KEY", "").strip(),
        make_timeout_seconds=_int("MAKE_TIMEOUT_SECONDS", 10),
    )

