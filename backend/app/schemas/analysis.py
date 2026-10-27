from __future__ import annotations

from typing import Any

from app.schemas.common import Schema


class Metric(Schema):
    key: str
    label: str
    value: float | int | None = None
    format: str
    description: str
    source_columns: list[str]
    start: str | None = None
    end: str | None = None


class AnalysisResult(Schema):
    roles: dict[str, str | None]
    revenue_source: str | None = None
    metrics: list[Metric]
    columns: list[dict[str, Any]]
    time_series: dict[str, Any] | None = None
    period_comparison: dict[str, Any] | None = None
    trend: dict[str, Any] | None = None
    breakdowns: dict[str, dict[str, Any]]
    distributions: dict[str, dict[str, Any]]
    correlations: list[dict[str, Any]]
    limitations: list[str]


class AggregateRow(Schema):
    group: str
    value: float | int | None = None
    records: int
    share: float | None = None


class AggregateResult(Schema):
    group_by: str
    aggregation: str
    rows: list[AggregateRow]
    total_groups: int


class TimePoint(Schema):
    period: str
    start: str
    end: str
    label: str
    value: float | int | None = None
    records: int
    partial: bool


class TimeSeriesResult(Schema):
    granularity: str
    aggregation: str
    points: list[TimePoint]
    excluded_rows: int
    first_date: str
    last_date: str


class HistogramBin(Schema):
    start: float | None = None
    end: float | None = None
    count: int


class DistributionResult(Schema):
    column: str
    bins: list[HistogramBin]
    count: int
    excluded_rows: int
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    min: float | None = None
    max: float | None = None


class InsightRequest(Schema):
    use_ai: bool = True


class Evidence(Schema):
    label: str
    value: str


class Insight(Schema):
    id: str
    category: str
    kind: str
    title: str
    statement: str
    evidence: list[Evidence]
    caveat: str | None = None
    source: str


class InsightResult(Schema):
    mode: str
    provider: str | None = None
    model: str | None = None
    generated_at: str
    insights: list[Insight]
    notices: list[str]
    limitations: list[str]
    data_sent: list[str]
    ai_error: str | None = None
