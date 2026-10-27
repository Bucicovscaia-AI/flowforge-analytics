from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_services
from app.config import APP_NAME, APP_VERSION
from app.integrations.ai.factory import provider_label
from app.schemas.system import ActivityItem, HealthResponse, SystemStatus
from app.services.container import Services

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthResponse, summary="Health check")
def health() -> dict:
    return {"status": "ok", "name": APP_NAME, "version": APP_VERSION}


@router.get("/system/status", response_model=SystemStatus, summary="Non-sensitive configuration and integration status")
def system_status(services: Services = Depends(get_services)) -> dict:
    settings = services.settings
    ai_ready = services.insights.ai_available
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "ai": {
            "configured": ai_ready,
            "provider": provider_label(settings.ai_provider) if ai_ready else None,
            "model": settings.ai_model if ai_ready else None,
            "data_policy": "Only aggregated results (metrics, grouped totals, period totals and quality findings) are sent. Raw rows are never sent.",
        },
        "automation_configured": services.automation.status()["configured"],
        "storage": {
            "engine": "SQLite + local files",
            "persistent": True,
            "description": "Datasets, cleaning history, reports and automation runs are stored on the server's disk and remain after a restart until deleted.",
        },
        "limits": {
            "max_upload_mb": settings.max_upload_mb,
            "max_rows": settings.max_rows,
            "max_columns": settings.max_columns,
            "accepted_extensions": [".csv", ".txt"],
        },
    }


@router.get("/activity", response_model=list[ActivityItem], summary="Recent activity")
def activity(
    limit: int = Query(20, ge=1, le=100),
    dataset_id: str | None = Query(None, pattern=r"^[0-9a-f]{32}$"),
    services: Services = Depends(get_services),
) -> list[dict]:
    return services.activity.list(limit, dataset_id)
