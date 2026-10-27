from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.common import Schema


class ColumnProfileOut(Schema):
    name: str
    inferred_type: str
    non_null_count: int
    missing_count: int
    missing_percent: float
    distinct_count: int
    invalid_count: int
    date_format: str | None = None
    sample_values: list[str]


class OperationRecord(Schema):
    id: int
    operation: str
    params: dict
    summary: str
    rows_before: int
    rows_after: int
    quality_before: float | None = None
    quality_after: float | None = None
    applied_at: str


class DatasetSummary(Schema):
    id: str
    name: str
    source_filename: str | None = None
    is_sample: bool
    status: str
    created_at: str
    updated_at: str
    original_row_count: int
    row_count: int
    column_count: int
    size_bytes: int
    encoding: str | None = None
    delimiter: str | None = None
    quality_score: float | None = None
    quality_grade: str | None = None
    warnings: list[str] = []


class RoleOption(Schema):
    label: str
    candidates: list[str]


class DatasetDetail(DatasetSummary):
    columns: list[ColumnProfileOut]
    roles: dict[str, str | None]
    role_options: dict[str, RoleOption]
    column_mapping: dict[str, str]
    operations: list[OperationRecord]


class DatasetRename(Schema):
    name: str = Field(min_length=1, max_length=120)


class ColumnMappingUpdate(Schema):
    mapping: dict[str, str | None] = Field(
        description="Role to column name. Use an empty string to switch a role off and null to return to automatic detection."
    )


class PreviewColumn(Schema):
    name: str
    type: str


class DatasetPreview(Schema):
    columns: list[PreviewColumn]
    rows: list[list[str | None]]
    offset: int
    limit: int
    total_rows: int


class SuggestedOperation(Schema):
    operation: str
    params: dict
    label: str


class QualityFinding(Schema):
    id: str
    rule: str
    severity: Literal["error", "warning", "info"]
    column: str | None = None
    title: str
    description: str
    impact: str
    affected_rows: int
    affected_cells: int
    affected_percent: float
    examples: list[str]
    suggestion: SuggestedOperation | None = None


class QualityReportOut(Schema):
    score: float
    grade: str
    row_count: int
    column_count: int
    total_cells: int
    missing_cells: int
    duplicate_rows: int
    counts: dict[str, int]
    findings: list[QualityFinding]
    method: str


class OperationParam(Schema):
    name: str
    label: str
    kind: str
    required: bool
    choices: list[str]
    default: str | None = None
    help: str


class OperationDescription(Schema):
    key: str
    label: str
    description: str
    consequence: str
    params: list[OperationParam]


class CleaningRequest(Schema):
    operation: str = Field(min_length=1, max_length=50)
    params: dict[str, str | None] = {}


class CleaningResult(Schema):
    operation: str
    params: dict
    rows_before: int
    rows_after: int
    rows_removed: int
    columns_before: int
    columns_after: int
    cells_changed: int
    changed: bool
    applied: bool
    summary: str
    warnings: list[str]
    quality_before: float | None = None
    quality_after: float | None = None
    message: str | None = None
