"""Application configuration loaded from environment variables.

Values are read once at start-up. A `.env` file in the backend directory or
the repository root is loaded if present, but real environment variables take
precedence. Secrets (AI keys, webhook URLs) are only ever read here and are
never returned by the API.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent

APP_NAME = "FlowForge Analytics"
APP_VERSION = "1.0.0"


def _load_env_files() -> None:
    for candidate in (BACKEND_DIR / ".env", REPO_ROOT / ".env"):
        if candidate.is_file():
            load_dotenv(candidate, override=False)


def _str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return max(minimum, int(raw))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return max(0.5, float(raw))
    except ValueError:
        return default


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _path(name: str, default: Path) -> Path:
    raw = _str(name)
    if not raw:
        return default
    path = Path(raw).expanduser()
    return path if path.is_absolute() else (BACKEND_DIR / path).resolve()


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    sample_data_path: Path
    max_upload_mb: int = 10
    max_rows: int = 500_000
    max_columns: int = 200
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
    frontend_dist_dir: Path | None = None
    public_base_url: str = ""
    storage_persistent: bool = True
    load_sample_on_startup: bool = False
    log_level: str = "INFO"

    ai_provider: str = ""
    ai_api_key: str = field(default="", repr=False)
    ai_model: str = "claude-opus-5-5"
    ai_timeout_seconds: float = 45.0
    ai_max_output_tokens: int = 4000

    make_webhook_url: str = field(default="", repr=False)
    make_webhook_secret: str = field(default="", repr=False)
    make_timeout_seconds: float = 10.0
    automation_trigger_on_report: bool = False
    report_link_secret: str = field(default="", repr=False)
    report_link_ttl_minutes: int = 60

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def database_path(self) -> Path:
        return self.data_dir / "flowforge.db"

    @property
    def datasets_dir(self) -> Path:
        return self.data_dir / "datasets"

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"

    @property
    def ai_configured(self) -> bool:
        return bool(self.ai_provider and self.ai_api_key)

    @property
    def webhook_configured(self) -> bool:
        return bool(self.make_webhook_url)


def load_settings() -> Settings:
    _load_env_files()
    origins = tuple(
        origin.strip()
        for origin in _str("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if origin.strip()
    )
    frontend_dist = _str("FRONTEND_DIST_DIR")
    provider = _str("AI_PROVIDER").lower()
    api_key = _str("AI_API_KEY")
    # An API key without an explicit provider defaults to the built-in provider.
    if api_key and not provider:
        provider = "anthropic"
    if provider in {"none", "disabled", "off"}:
        provider = ""
    return Settings(
        data_dir=_path("DATA_DIR", BACKEND_DIR / "data"),
        sample_data_path=_path("SAMPLE_DATA_PATH", REPO_ROOT / "sample-data" / "flowforge-retail-sample.csv"),
        max_upload_mb=_int("MAX_UPLOAD_MB", 10),
        max_rows=_int("MAX_ROWS", 500_000),
        max_columns=_int("MAX_COLUMNS", 200),
        cors_origins=origins,
        frontend_dist_dir=_path("FRONTEND_DIST_DIR", BACKEND_DIR) if frontend_dist else None,
        # Render sets RENDER_EXTERNAL_URL for every web service, so links work there without extra configuration.
        public_base_url=(_str("PUBLIC_BASE_URL") or _str("RENDER_EXTERNAL_URL")).rstrip("/"),
        storage_persistent=_bool("STORAGE_PERSISTENT", True),
        load_sample_on_startup=_bool("LOAD_SAMPLE_ON_STARTUP", False),
        log_level=_str("LOG_LEVEL", "INFO").upper(),
        ai_provider=provider,
        ai_api_key=api_key,
        ai_model=_str("AI_MODEL") or "claude-opus-5-5",
        ai_timeout_seconds=_float("AI_TIMEOUT_SECONDS", 45.0),
        ai_max_output_tokens=_int("AI_MAX_OUTPUT_TOKENS", 4000, minimum=500),
        make_webhook_url=_str("MAKE_WEBHOOK_URL"),
        make_webhook_secret=_str("MAKE_WEBHOOK_SECRET"),
        make_timeout_seconds=_float("MAKE_TIMEOUT_SECONDS", 10.0),
        automation_trigger_on_report=_bool("AUTOMATION_TRIGGER_ON_REPORT", False),
        report_link_secret=_str("REPORT_LINK_SECRET"),
        report_link_ttl_minutes=min(_int("REPORT_LINK_TTL_MINUTES", 60, minimum=5), 7 * 24 * 60),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
