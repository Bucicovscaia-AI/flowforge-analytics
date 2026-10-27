from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.common import Schema


class EventType(Schema):
    type: str
    description: str


class AutomationStatus(Schema):
    provider: str
    configured: bool
    configuration_problem: str | None = None
    signing_enabled: bool
    trigger_on_report: bool
    timeout_seconds: float
    event_types: list[EventType]


class AutomationTrigger(Schema):
    event_type: Literal["dataset.analysed", "report.generated", "automation.test"]
    dataset_id: str | None = Field(default=None, min_length=32, max_length=32)
    report_id: str | None = Field(default=None, min_length=32, max_length=32)


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
