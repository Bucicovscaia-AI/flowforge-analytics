from __future__ import annotations

from fastapi import Path, Request

from app.services.container import Services

DatasetId = Path(pattern=r"^[0-9a-f]{32}$", description="Dataset identifier")
ReportId = Path(pattern=r"^[0-9a-f]{32}$", description="Report identifier")


def get_services(request: Request) -> Services:
    return request.app.state.services
