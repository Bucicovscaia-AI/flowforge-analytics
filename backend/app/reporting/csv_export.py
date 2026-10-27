"""CSV export helpers.

Text cells that begin with characters spreadsheet applications interpret as
formulas (=, +, -, @) are prefixed with an apostrophe so that opening an
export cannot trigger formula execution. Numeric values are left unchanged.
"""

from __future__ import annotations

import io

import pandas as pd

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _neutralise(value):
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        try:
            float(value)
            return value
        except ValueError:
            return "'" + value
    return value


def frame_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    safe = frame.copy()
    safe.columns = [_neutralise(str(column)) for column in safe.columns]
    for column in safe.columns:
        if not pd.api.types.is_numeric_dtype(safe[column]):
            safe[column] = safe[column].map(_neutralise)
    buffer = io.StringIO()
    safe.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def report_to_csv_bytes(document: dict) -> bytes:
    """Flatten a report's tabular results into one long-format CSV."""
    rows: list[dict] = []

    def add(section: str, item: str, measure: str, value, detail: str = "") -> None:
        rows.append({"section": section, "item": item, "measure": measure, "value": value, "detail": detail})

    add("report", "title", "text", document["title"])
    add("report", "generated_at", "timestamp", document["generated_at"])
    add("report", "dataset", "text", document["dataset"]["name"])
    add("report", "records", "count", document["dataset"]["record_count"])
    for metric in document["metrics"]:
        if metric["format"] == "date_range":
            add("metrics", metric["label"], "date_range", f"{metric['start']} to {metric['end']}")
        else:
            add("metrics", metric["label"], metric["format"], metric["value"], metric.get("description", ""))
    series = document.get("time_series")
    if series:
        for point in series["points"]:
            add(
                f"time_series_{series['granularity']}",
                point["label"],
                series["aggregation"],
                point["value"],
                f"records={point['records']}" + ("; partial period" if point["partial"] else ""),
            )
    for role, breakdown in document.get("breakdowns", {}).items():
        for row in breakdown["rows"]:
            add(
                f"breakdown_{role}",
                row["group"],
                breakdown["measure"],
                row.get("revenue") if breakdown["measure"] == "revenue" else row["records"],
                f"records={row['records']}; share={row.get('share')}%",
            )
    quality = document["quality"]
    add("quality", "score", "score", quality["score"], quality["grade"])
    for finding in quality["findings"]:
        add("quality_finding", finding["title"], finding["severity"], finding["affected_rows"], finding["description"])
    return frame_to_csv_bytes(pd.DataFrame(rows, columns=["section", "item", "measure", "value", "detail"]))
