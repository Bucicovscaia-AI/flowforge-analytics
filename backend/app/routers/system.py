"""Health, configuration and integration-test endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.config import APP_VERSION, Settings
from app.deps import get_settings
from app.services.csv_loader import OPTIONAL_COLUMNS, REQUIRED_COLUMNS
from app.services.cleaning import RULES
from app.services.webhook import WebhookError, describe_target, send_event

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health() -> dict:
    """Lets the frontend (and Make.com) check the API is running."""
    return {"status": "ok", "version": APP_VERSION}


@router.get("/config")
def config(settings: Settings = Depends(get_settings)) -> dict:
    """Feature flags for the interface. Secrets are never included."""
    return {
        "version": APP_VERSION,
        "max_upload_mb": settings.max_upload_mb,
        "max_rows": settings.max_rows,
        "required_columns": REQUIRED_COLUMNS,
        "optional_columns": OPTIONAL_COLUMNS,
        "cleaning_rules": [{"rule": k, "description": v} for k, v in RULES.items()],
        "ai": {"configured": settings.ai_configured, "model": settings.ai_model if settings.ai_configured else None},
        "webhook": {
            "configured": settings.webhook_configured,
            "target_host": describe_target(settings),
            "api_key_set": bool(settings.make_webhook_api_key),
        },
    }


@router.post("/integrations/make/test")
def test_webhook(settings: Settings = Depends(get_settings)) -> dict:
    """Send a small 'test.ping' event so the Make scenario can be checked."""
    try:
        return send_event({"event": "test.ping", "message": "FlowForge webhook test"}, settings)
    except WebhookError as exc:
        status = 409 if not settings.webhook_configured else 502
        raise HTTPException(status_code=status, detail=str(exc)) from None
