from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import ReportId, get_services
from app.schemas.reports import ReportCreated, ReportRequest, ReportSummary
from app.services.container import Services

router = APIRouter(tags=["Reports"])


@router.post("/reports", response_model=ReportCreated, status_code=status.HTTP_201_CREATED, summary="Generate a report")
def create_report(body: ReportRequest, services: Services = Depends(get_services)) -> dict:
    return services.reports.generate(body.dataset_id, body.title, body.use_ai)


@router.get("/reports", response_model=list[ReportSummary], summary="Report history")
def list_reports(
    dataset_id: str | None = Query(None, pattern=r"^[0-9a-f]{32}$"),
    limit: int = Query(100, ge=1, le=500),
    services: Services = Depends(get_services),
) -> list[dict]:
    return services.reports.list(dataset_id, limit)


@router.get("/reports/{report_id}", response_model=ReportSummary, summary="Report metadata")
def get_report(report_id: str = ReportId, services: Services = Depends(get_services)) -> dict:
    return services.reports.get(report_id)


@router.get("/reports/{report_id}/content", summary="Full report content as JSON")
def report_content(report_id: str = ReportId, services: Services = Depends(get_services)) -> dict:
    return services.reports.document(report_id)


@router.get("/reports/{report_id}/download", summary="Download a report file")
def download_report(
    report_id: str = ReportId,
    format: Literal["html", "pdf", "csv", "json"] = "html",
    inline: bool = Query(False, description="Display in the browser instead of downloading"),
    services: Services = Depends(get_services),
) -> Response:
    content, media_type, filename = services.reports.file(report_id, format)
    disposition = "inline" if inline and format in ("html", "pdf") else "attachment"
    headers = {"Content-Disposition": f'{disposition}; filename="{filename}"'}
    if format == "html":
        # The report is static: block scripts and external requests if it is opened from the API.
        headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; img-src data:"
    return Response(content, media_type=media_type, headers=headers)


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a report")
def delete_report(report_id: str = ReportId, services: Services = Depends(get_services)) -> Response:
    services.reports.delete(report_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
