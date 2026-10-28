"""Assemble a report document from analysis, quality and insight results.

The document is a plain dictionary snapshot. Renderers (HTML, PDF, CSV) only
format this snapshot; they never recalculate figures, so every format shows
the same numbers.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

STANDARD_LIMITATIONS = [
    "Figures describe the dataset as imported and cleaned in FlowForge; they are only as accurate as the source data.",
    "Rule-based and AI-generated insights are aids to interpretation, not verified conclusions.",
    "Relationships between values are correlations and do not show cause and effect.",
]


def build_report_document(
    *, report_id: str, title: str, dataset: dict, operations: list[dict], analysis: dict, quality: dict, insights: dict
) -> dict:
    cleaning_steps = [operation["summary"] for operation in operations]
    scope = (
        f"All {dataset['row_count']:,} records and {dataset['column_count']} columns in the working copy of '{dataset['name']}'."
    )
    if dataset["row_count"] != dataset["original_row_count"]:
        scope += f" The original import contained {dataset['original_row_count']:,} records."
    limitations = list(dict.fromkeys(analysis.get("limitations", []) + insights.get("limitations", []) + STANDARD_LIMITATIONS))
    if dataset.get("is_sample"):
        limitations.insert(0, "This report uses synthetic demonstration data. It does not describe a real business.")
    return {
        "id": report_id,
        "title": title,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "status": "completed",
        "dataset": {
            "id": dataset["id"],
            "name": dataset["name"],
            "is_sample": bool(dataset.get("is_sample")),
            "record_count": dataset["row_count"],
            "column_count": dataset["column_count"],
            "original_record_count": dataset["original_row_count"],
            "imported_at": dataset["created_at"],
        },
        "scope": {"description": scope, "cleaning_steps": cleaning_steps, "roles": analysis.get("roles", {})},
        "metrics": analysis.get("metrics", []),
        "quality": {
            "score": quality["score"],
            "grade": quality["grade"],
            "counts": quality["counts"],
            "missing_cells": quality["missing_cells"],
            "duplicate_rows": quality["duplicate_rows"],
            "findings": quality["findings"][:12],
            "method": quality["method"],
        },
        "time_series": analysis.get("time_series"),
        "period_comparison": analysis.get("period_comparison"),
        "trend": analysis.get("trend"),
        "breakdowns": analysis.get("breakdowns", {}),
        "correlations": analysis.get("correlations", []),
        "insights": {
            "mode": insights["mode"],
            "provider": insights.get("provider"),
            "model": insights.get("model"),
            "items": insights["insights"],
            "notices": insights.get("notices", []),
        },
        "limitations": limitations,
    }


def safe_download_name(title: str, extension: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-").lower()[:60] or "report"
    return f"{slug}.{extension}"


def format_value(value, fmt: str) -> str:
    if value is None:
        return "–"
    if fmt == "currency":
        return f"{value:,.2f}"
    if fmt == "integer":
        return f"{int(value):,}"
    if fmt == "percent":
        return f"{value:.1f}%"
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".") if value % 1 else f"{value:,.0f}"
    return f"{value:,}" if isinstance(value, int) else str(value)


def format_metric(metric: dict) -> str:
    if metric.get("format") == "date_range":
        return f"{metric['start']} to {metric['end']}"
    return format_value(metric.get("value"), metric.get("format", "number"))


ROLE_TITLES = {"category": "Category", "product": "Product", "region": "Region", "status": "Status"}
INSIGHT_SOURCE_LABELS = {"ai": "AI-generated", "rule_based": "Rule-based"}
KIND_LABELS = {"fact": "Measured fact", "interpretation": "Interpretation", "suggestion": "Suggestion"}
