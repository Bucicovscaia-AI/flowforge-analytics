from __future__ import annotations

from pydantic import Field

from app.schemas.automation import AutomationRun
from app.schemas.common import Schema


class ReportRequest(Schema):
    dataset_id: str = Field(min_length=32, max_length=32)
    title: str | None = Field(default=None, max_length=120)
    use_ai: bool = True


class ReportSummary(Schema):
    id: str
    title: str
    dataset_id: str | None = None
    dataset_name: str
    created_at: str
    status: str
    insight_mode: str | None = None
    record_count: int | None = None
    formats: list[str]
    error: str | None = None


class ReportCreated(ReportSummary):
    automation_run: AutomationRun | None = None
