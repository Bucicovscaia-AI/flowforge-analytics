"""Report generation, history, download and Make.com notification."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.config import Settings
from app.deps import get_settings, get_store, require_analysis
from app.services.pipeline import new_id
from app.services.report_pdf import build_report_pdf
from app.services.webhook import WebhookError, build_report_payload, send_event
from app.storage import Store

router = APIRouter(prefix="/api", tags=["reports"])


class ReportRequest(BaseModel):
    analysis_id: str
    title: str = Field(default="", max_length=120)
    include_insights: bool = True
    notify_make: bool = False


def _notify(report: dict, analysis: dict, settings: Settings, store: Store) -> dict:
    insights = analysis.get("insights") if report["insight_source"] == "ai" else None
    try:
        result = send_event(build_report_payload(report, analysis, insights), settings)
        status = {"status": "delivered", "message": f"Delivered (HTTP {result['status_code']})", "event_id": result["event_id"]}
    except WebhookError as exc:
        status = {"status": "failed", "message": str(exc)}
    status["at"] = datetime.now(timezone.utc).isoformat()
    store.update_report(report["id"], webhook=status)
    return status


@router.post("/reports", status_code=201)
async def create_report(body: ReportRequest, settings: Settings = Depends(get_settings), store: Store = Depends(get_store)) -> dict:
    analysis = require_analysis(store, body.analysis_id)
    now = datetime.now(timezone.utc)
    title = body.title.strip() or f"Sales performance report: {analysis['dataset']['file_name']}"
    insights = analysis.get("insights") if body.include_insights else None
    pdf = await run_in_threadpool(build_report_pdf, analysis, title, insights, now)
    report = {
        "id": new_id("rpt"),
        "analysis_id": analysis["id"],
        "title": title,
        "dataset": analysis["dataset"]["file_name"],
        "synthetic": analysis["dataset"]["synthetic"],
        "created_at": now.isoformat(),
        "size_bytes": len(pdf),
        "insight_source": insights["source"] if insights else "rule-based",
        "total_revenue": analysis["kpis"]["summary"]["total_revenue"],
        "webhook": {"status": "not_requested" if settings.webhook_configured else "not_configured"},
    }
    store.add_report(report, pdf)
    if body.notify_make and settings.webhook_configured:
        report["webhook"] = await run_in_threadpool(_notify, report, analysis, settings, store)
    return report


@router.get("/reports")
def list_reports(store: Store = Depends(get_store)) -> list[dict]:
    return store.list_reports()


@router.get("/reports/{report_id}/download")
def download_report(report_id: str, store: Store = Depends(get_store)) -> FileResponse:
    meta = store.get_report(report_id)
    path = store.report_path(report_id)
    if meta is None or path is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    return FileResponse(path, media_type="application/pdf", filename=f"flowforge-report-{report_id}.pdf")


@router.post("/reports/{report_id}/notify")
async def notify_report(report_id: str, settings: Settings = Depends(get_settings), store: Store = Depends(get_store)) -> dict:
    report = store.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    if not settings.webhook_configured:
        raise HTTPException(status_code=409, detail="The Make.com webhook is not configured (set MAKE_WEBHOOK_URL on the server).")
    analysis = require_analysis(store, report["analysis_id"])
    status = await run_in_threadpool(_notify, report, analysis, settings, store)
    if status["status"] != "delivered":
        raise HTTPException(status_code=502, detail=status["message"])
    return status


@router.delete("/reports/{report_id}", status_code=204)
def delete_report(report_id: str, store: Store = Depends(get_store)) -> None:
    if not store.delete_report(report_id):
        raise HTTPException(status_code=404, detail="Report not found.")
