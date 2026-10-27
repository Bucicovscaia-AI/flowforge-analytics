from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_services
from app.schemas.automation import AutomationRun, AutomationStatus, AutomationTrigger
from app.services.container import Services

router = APIRouter(tags=["Automation"])


@router.get("/automation/status", response_model=AutomationStatus, summary="Make.com integration status")
def automation_status(services: Services = Depends(get_services)) -> dict:
    return services.automation.status()


@router.post("/automation/preview", summary="Show the payload that would be sent, without sending it")
def preview_payload(body: AutomationTrigger, services: Services = Depends(get_services)) -> dict:
    return services.automation.build_payload(body.event_type, body.dataset_id, body.report_id)


@router.post("/automation/trigger", response_model=AutomationRun, summary="Send an event to the configured webhook")
def trigger(body: AutomationTrigger, services: Services = Depends(get_services)) -> dict:
    return services.automation.trigger(body.event_type, body.dataset_id, body.report_id)


@router.get("/automation/runs", response_model=list[AutomationRun], summary="Automation delivery history")
def runs(limit: int = Query(50, ge=1, le=200), services: Services = Depends(get_services)) -> list[dict]:
    return services.automation.list_runs(limit)
