from __future__ import annotations

from app.schemas.common import Schema


class HealthResponse(Schema):
    status: str
    name: str
    version: str


class AIStatus(Schema):
    configured: bool
    provider: str | None = None
    model: str | None = None
    data_policy: str


class StorageStatus(Schema):
    engine: str
    persistent: bool
    description: str


class Limits(Schema):
    max_upload_mb: int
    max_rows: int
    max_columns: int
    accepted_extensions: list[str]


class SystemStatus(Schema):
    name: str
    version: str
    ai: AIStatus
    automation_configured: bool
    storage: StorageStatus
    limits: Limits


class ActivityItem(Schema):
    id: int
    kind: str
    message: str
    dataset_id: str | None = None
    report_id: str | None = None
    created_at: str
