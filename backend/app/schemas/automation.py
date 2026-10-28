from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.common import Schema


class EventType(Schema):
    type: str
    description: str


class PdfLinks(Schema):
    enabled: bool
    problem: str | None = None
    ttl_minutes: int
    survive_restart: bool
    max_pdf_mb: int


class AutomationStatus(Schema):
    provider: str
    configured: bool
    configuration_problem: str | None = None
    signing_enabled: bool
    trigger_on_report: bool
    timeout_seconds: float
    event_types: list[EventType]
    schema_version: int
    pdf_links: PdfLinks


class AutomationTrigger(Schema):
    event_type: Literal["dataset.analysed", "report.generated", "automation.test"]
    dataset_id: str | None = Field(default=None, min_length=32, max_length=32)
    report_id: str | None = Field(default=None, min_length=32, max_length=32)
    resend: bool = False


class AutomationConfirmation(Schema):
    status: Literal["sent", "failed"]
    message: str | None = Field(default=None, max_length=300)


class AutomationRun(Schema):
    id: str
    event_type: str
    trigger: str
    dataset_id: str | None = None
    report_id: str | None = None
    status: str
    http_status: int | None = None
    message: str
    duration_ms: int | None = None
    payload: dict
    created_at: str
    pdf_downloaded_at: str | None = None
    confirmation_status: str | None = None
    confirmation_message: str | None = None
    confirmed_at: str | None = None
