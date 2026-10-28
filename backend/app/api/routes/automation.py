from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query, Response

from app.api.deps import get_services
from app.schemas.automation import AutomationConfirmation, AutomationRun, AutomationStatus, AutomationTrigger
from app.services.container import Services

router = APIRouter(tags=["Automation"])

RunId = Path(pattern=r"^[0-9a-f]{32}$", description="Automation event identifier")
Expires = Query(..., ge=0, description="Link expiry as a Unix timestamp")
Signature = Query(..., pattern=r"^[0-9a-f]{64}$", description="Link signature")


@router.get("/automation/status", response_model=AutomationStatus, summary="Make.com integration status")
def automation_status(services: Services = Depends(get_services)) -> dict:
    return services.automation.status()


@router.post("/automation/preview", summary="Show the payload that would be sent, without sending it")
def preview_payload(body: AutomationTrigger, services: Services = Depends(get_services)) -> dict:
    return services.automation.preview(body.event_type, body.dataset_id, body.report_id)


@router.post("/automation/trigger", response_model=AutomationRun, summary="Send an event to the configured webhook")
def trigger(body: AutomationTrigger, services: Services = Depends(get_services)) -> dict:
    return services.automation.trigger(body.event_type, body.dataset_id, body.report_id, resend=body.resend)


@router.get("/automation/runs", response_model=list[AutomationRun], summary="Automation delivery history")
def runs(limit: int = Query(50, ge=1, le=200), services: Services = Depends(get_services)) -> list[dict]:
    return services.automation.list_runs(limit)


@router.get(
    "/automation/runs/{run_id}/report.pdf",
    summary="Download the report PDF of an event (signed link for Make.com)",
    response_class=Response,
)
def signed_report_pdf(
    run_id: str = RunId, expires: int = Expires, signature: str = Signature, services: Services = Depends(get_services)
) -> Response:
    content, filename = services.automation.signed_pdf(run_id, expires, signature)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"}
    return Response(content, media_type="application/pdf", headers=headers)


@router.post(
    "/automation/runs/{run_id}/confirmation",
    response_model=AutomationRun,
    summary="Record whether the scenario's action succeeded (signed link for Make.com)",
)
def confirm_run(
    body: AutomationConfirmation,
    run_id: str = RunId,
    expires: int = Expires,
    signature: str = Signature,
    services: Services = Depends(get_services),
) -> dict:
    return services.automation.confirm(run_id, expires, signature, body.status, body.message)
