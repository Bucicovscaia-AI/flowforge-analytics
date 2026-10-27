"""Analytics engine.

Pure functions over pandas DataFrames, independent of the web layer. General
statistics work for any tabular data; business metrics (revenue, quantity,
category performance) are added only when the relevant columns exist, either
detected automatically or mapped by the user.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.engine.profiling import (
    BOOLEAN,
    CATEGORICAL,
    DATETIME,
    IDENTIFIER,
    NUMERIC,
    TEXT,
    DatasetProfile,
)

MISSING_LABEL = "(missing)"
GRANULARITIES = {"day": "D", "week": "W-SUN", "month": "M", "quarter": "Q", "year": "Y"}
AGGREGATIONS = {"sum", "mean", "median", "count", "min", "max"}
DIMENSION_ROLES = ("category", "product", "region", "status")


class AnalysisError(ValueError):
    """Raised when a requested analysis cannot be performed on the data."""


@dataclass
class AnalysisContext:
    typed: pd.DataFrame
    profile: DatasetProfile
    roles: dict[str, str | None]


def to_number(value) -> float | int | None:
    """Convert numpy/pandas scalars to JSON-safe Python numbers."""
    if value is None or (isinstance(value, float) and math.isnan(value)) or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    if isinstance(value, (int,)):
        return value
    return value


def _round(value, digits: int = 4):
    number = to_number(value)
    return round(number, digits) if isinstance(number, float) else number


# ---------------------------------------------------------------------------
# Revenue resolution
# ---------------------------------------------------------------------------


def revenue_series(context: AnalysisContext) -> tuple[pd.Series | None, str | None]:
    """Return per-row revenue and how it was obtained ("column" or "derived")."""
    revenue = context.roles.get("revenue")
    if revenue:
        return context.typed[revenue], "column"
    quantity, price = context.roles.get("quantity"), context.roles.get("unit_price")
    if quantity and price:
        return (context.typed[quantity] * context.typed[price]).rename("revenue"), "derived"
    return None, None


# ---------------------------------------------------------------------------
# Building blocks used by the API and the visualisation builder
# ---------------------------------------------------------------------------


def _group_labels(series: pd.Series) -> pd.Series:
    labels = series.dt.strftime("%Y-%m-%d") if pd.api.types.is_datetime64_any_dtype(series) else series.astype("string")
    return labels.fillna(MISSING_LABEL)


def aggregate(
    frame: pd.DataFrame,
    group_by: str,
    values: pd.Series | None = None,
    agg: str = "sum",
    top_n: int | None = None,
) -> dict:
    """Aggregate `values` (or count rows) by the distinct values of one column."""
    if group_by not in frame.columns:
        raise AnalysisError(f"Column '{group_by}' does not exist.")
    if agg not in AGGREGATIONS:
        raise AnalysisError(f"Unsupported aggregation '{agg}'.")
    labels = _group_labels(frame[group_by])
    if values is None or agg == "count":
        grouped = labels.groupby(labels).size().astype(float)
        records = grouped
        agg = "count"
    else:
        grouped = values.groupby(labels).agg(agg)
        records = labels.groupby(labels).size()
    grouped = grouped.sort_values(ascending=False)
    total = float(values.sum()) if (values is not None and agg == "sum") else float(len(frame))
    rows = [
        {
            "group": str(group),
            "value": _round(value),
            "records": int(records.get(group, 0)),
            "share": _round(value / total * 100, 2) if agg in ("sum", "count") and total else None,
        }
        for group, value in grouped.items()
    ]
    total_groups = len(rows)
    if top_n and len(rows) > top_n:
        rows = rows[:top_n]
    return {"group_by": group_by, "aggregation": agg, "rows": rows, "total_groups": total_groups}


def choose_granularity(dates: pd.Series) -> str:
    valid = dates.dropna()
    if valid.empty:
        return "month"
    span = (valid.max() - valid.min()).days
    if span <= 45:
        return "day"
    if span <= 210:
        return "week"
    if span <= 365 * 4:
        return "month"
    return "quarter"


def time_series(
    dates: pd.Series,
    values: pd.Series | None = None,
    agg: str = "sum",
    granularity: str = "auto",
) -> dict:
    """Aggregate values (or count rows) per calendar period."""
    if not pd.api.types.is_datetime64_any_dtype(dates):
        raise AnalysisError("A date column is required for a time series.")
    valid = dates.notna()
    excluded = int((~valid).sum())
    if not valid.any():
        raise AnalysisError("The date column has no readable dates.")
    if granularity == "auto":
        granularity = choose_granularity(dates)
    if granularity not in GRANULARITIES:
        raise AnalysisError(f"Unsupported granularity '{granularity}'.")
    if agg not in AGGREGATIONS:
        raise AnalysisError(f"Unsupported aggregation '{agg}'.")

    periods = dates[valid].dt.to_period(GRANULARITIES[granularity])
    counts = periods.groupby(periods).size()
    if values is None or agg == "count":
        aggregated = counts.astype(float)
        agg = "count"
    else:
        aggregated = values[valid].groupby(periods).agg(agg)
    full_range = pd.period_range(periods.min(), periods.max(), freq=periods.min().freq)
    aggregated = aggregated.reindex(full_range)
    counts = counts.reindex(full_range, fill_value=0)

    first_date, last_date = dates[valid].min(), dates[valid].max()
    points = []
    for period, value in aggregated.items():
        start, end = period.start_time, period.end_time
        partial = granularity != "day" and (first_date > start.normalize() or last_date < end.normalize())
        if agg in ("sum", "count") and pd.isna(value):
            value = 0.0
        points.append(
            {
                "period": str(period),
                "start": start.strftime("%Y-%m-%d"),
                "end": end.strftime("%Y-%m-%d"),
                "label": _period_label(period, granularity),
                "value": _round(value),
                "records": int(counts.get(period, 0)),
                "partial": bool(partial),
            }
        )
    return {
        "granularity": granularity,
        "aggregation": agg,
        "points": points,
        "excluded_rows": excluded,
        "first_date": first_date.strftime("%Y-%m-%d"),
        "last_date": last_date.strftime("%Y-%m-%d"),
    }


def _period_label(period: pd.Period, granularity: str) -> str:
    if granularity == "day":
        return period.start_time.strftime("%d %b %Y")
    if granularity == "week":
        return "Week of " + period.start_time.strftime("%d %b %Y")
    if granularity == "month":
        return period.start_time.strftime("%b %Y")
    if granularity == "quarter":
        return f"Q{period.quarter} {period.year}"
    return str(period.year)


def distribution(values: pd.Series, bins: int = 20) -> dict:
    numbers = pd.to_numeric(values, errors="coerce").dropna()
    if numbers.empty:
        raise AnalysisError("The column has no numeric values to show a distribution for.")
    bins = max(1, min(int(bins), 60))
    if numbers.nunique() == 1:
        edges = np.array([numbers.iloc[0], numbers.iloc[0]])
        counts = np.array([len(numbers)])
    else:
        counts, edges = np.histogram(numbers, bins=bins)
    return {
        "bins": [
            {"start": _round(edges[index]), "end": _round(edges[index + 1]), "count": int(count)}
            for index, count in enumerate(counts)
        ],
        "count": int(len(numbers)),
        "excluded_rows": int(len(values) - len(numbers)),
        "mean": _round(numbers.mean()),
        "median": _round(numbers.median()),
        "std": _round(numbers.std()) if len(numbers) > 1 else None,
        "min": _round(numbers.min()),
        "max": _round(numbers.max()),
    }


def period_comparison(series: dict) -> dict | None:
    """Compare the latest complete period with the one before it."""
    points = series["points"]
    if len(points) < 2:
        return None
    candidates = points
    note = None
    if points[-1]["partial"] and len(points) >= 3:
        candidates = points[:-1]
        note = f"The latest period ({points[-1]['label']}) is incomplete and was excluded from the comparison."
    current, previous = candidates[-1], candidates[-2]
    if current["value"] is None or previous["value"] is None:
        return None
    change = current["value"] - previous["value"]
    change_percent = round(change / previous["value"] * 100, 2) if previous["value"] else None
    if current["partial"] or previous["partial"]:
        note = (note + " " if note else "") + "At least one compared period contains partial data."
    return {
        "granularity": series["granularity"],
        "aggregation": series["aggregation"],
        "current": {"label": current["label"], "value": current["value"], "records": current["records"]},
        "previous": {"label": previous["label"], "value": previous["value"], "records": previous["records"]},
        "change": _round(change),
        "change_percent": change_percent,
        "note": note,
    }


def trend_direction(series: dict) -> dict | None:
    """Least-squares slope across complete periods, expressed relative to the mean."""
    points = [point for point in series["points"] if not point["partial"] and point["value"] is not None]
    if len(points) < 4:
        return None
    values = np.array([point["value"] for point in points], dtype=float)
    mean = values.mean()
    if mean == 0:
        return None
    slope = np.polyfit(np.arange(len(values)), values, 1)[0]
    relative = slope / abs(mean) * 100
    direction = "upward" if relative > 2 else "downward" if relative < -2 else "flat"
    return {
        "direction": direction,
        "slope_per_period": _round(slope),
        "relative_slope_percent": round(float(relative), 2),
        "periods": len(points),
        "first_label": points[0]["label"],
        "last_label": points[-1]["label"],
    }


def correlations(context: AnalysisContext, limit: int = 5) -> list[dict]:
    columns = [
        column.name
        for column in context.profile.columns
        if column.inferred_type == NUMERIC and context.typed[column.name].nunique() > 2
    ]
    if len(columns) < 2 or len(context.typed) < 10:
        return []
    matrix = context.typed[columns].corr(method="pearson", min_periods=10)
    role_columns = {context.roles.get(role) for role in ("revenue", "quantity", "unit_price")} - {None}
    pairs = []
    for i, first in enumerate(columns):
        for second in columns[i + 1 :]:
            value = matrix.loc[first, second]
            if pd.isna(value) or abs(value) < 0.3:
                continue
            pairs.append(
                {
                    "column_a": first,
                    "column_b": second,
                    "coefficient": round(float(value), 3),
                    "strength": "strong" if abs(value) >= 0.7 else "moderate",
                    "expected": first in role_columns and second in role_columns,
                }
            )
    pairs.sort(key=lambda pair: abs(pair["coefficient"]), reverse=True)
    return pairs[:limit]


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------


def column_summaries(context: AnalysisContext) -> list[dict]:
    summaries = []
    for column in context.profile.columns:
        values = context.typed[column.name]
        summary = {
            "name": column.name,
            "type": column.inferred_type,
            "non_null": column.non_null_count,
            "missing": column.missing_count,
            "missing_percent": column.missing_percent,
            "distinct": column.distinct_count,
            "invalid": column.invalid_count,
        }
        if column.inferred_type == NUMERIC:
            numbers = values.dropna()
            if not numbers.empty:
                summary["stats"] = {
                    "count": int(numbers.count()),
                    "sum": _round(numbers.sum()),
                    "mean": _round(numbers.mean()),
                    "std": _round(numbers.std()) if len(numbers) > 1 else None,
                    "min": _round(numbers.min()),
                    "p25": _round(numbers.quantile(0.25)),
                    "median": _round(numbers.median()),
                    "p75": _round(numbers.quantile(0.75)),
                    "max": _round(numbers.max()),
                }
        elif column.inferred_type == DATETIME:
            dates = values.dropna()
            if not dates.empty:
                summary["stats"] = {
                    "min": dates.min().strftime("%Y-%m-%d"),
                    "max": dates.max().strftime("%Y-%m-%d"),
                    "span_days": int((dates.max() - dates.min()).days),
                }
        elif column.inferred_type in (CATEGORICAL, TEXT, BOOLEAN, IDENTIFIER):
            counts = values.dropna().astype("string").value_counts().head(5)
            summary["top_values"] = [{"value": str(value), "count": int(count)} for value, count in counts.items()]
        summaries.append(summary)
    return summaries


def _metric(key: str, label: str, value, fmt: str, description: str, source: list[str]) -> dict:
    return {
        "key": key,
        "label": label,
        "value": _round(value, 2) if fmt != "integer" else to_number(value),
        "format": fmt,
        "description": description,
        "source_columns": source,
    }


def business_metrics(context: AnalysisContext) -> tuple[list[dict], list[str]]:
    metrics: list[dict] = []
    notes: list[str] = []
    roles = context.roles
    rows = len(context.typed)
    metrics.append(_metric("records", "Total records", rows, "integer", "Number of rows in the dataset.", []))
    metrics.append(_metric("columns", "Columns", context.typed.shape[1], "integer", "Number of columns in the dataset.", []))

    revenue, source = revenue_series(context)
    if revenue is not None:
        valid = revenue.dropna()
        source_columns = [roles["revenue"]] if source == "column" else [roles["quantity"], roles["unit_price"]]
        if source == "derived":
            notes.append(
                f"Revenue is calculated as {roles['quantity']} × {roles['unit_price']} because no revenue column was found."
            )
        if len(valid) < rows:
            notes.append(f"{rows - len(valid):,} rows have no usable revenue value and are excluded from revenue metrics.")
        metrics.append(
            _metric(
                "total_revenue",
                "Total revenue",
                valid.sum(),
                "currency",
                "Sum of revenue across all rows with a value.",
                source_columns,
            )
        )
        if not valid.empty:
            metrics.append(
                _metric(
                    "average_transaction_value",
                    "Average transaction value",
                    valid.mean(),
                    "currency",
                    "Mean revenue per row, treating each row as one transaction.",
                    source_columns,
                )
            )
            metrics.append(
                _metric(
                    "median_transaction_value",
                    "Median transaction value",
                    valid.median(),
                    "currency",
                    "Middle revenue value; less affected by unusually large transactions than the mean.",
                    source_columns,
                )
            )
    else:
        notes.append(
            "No revenue column was found, so revenue metrics are unavailable. Map a numeric column as revenue on the Analysis page if one exists."
        )

    if roles.get("quantity"):
        quantity = context.typed[roles["quantity"]].dropna()
        metrics.append(
            _metric(
                "total_quantity", "Total quantity", quantity.sum(), "number", "Sum of the quantity column.", [roles["quantity"]]
            )
        )
    for role, key, label in (
        ("category", "categories", "Categories"),
        ("product", "products", "Products"),
        ("region", "regions", "Regions"),
    ):
        column = roles.get(role)
        if column:
            metrics.append(
                _metric(key, label, int(context.typed[column].nunique()), "integer", f"Distinct values in '{column}'.", [column])
            )
    if roles.get("date"):
        dates = context.typed[roles["date"]].dropna()
        if not dates.empty:
            metrics.append(
                {
                    "key": "date_range",
                    "label": "Date range",
                    "value": None,
                    "format": "date_range",
                    "start": dates.min().strftime("%Y-%m-%d"),
                    "end": dates.max().strftime("%Y-%m-%d"),
                    "description": f"Earliest and latest value in '{roles['date']}'.",
                    "source_columns": [roles["date"]],
                }
            )
    return metrics, notes


def dimension_breakdowns(context: AnalysisContext, top_n: int = 15) -> dict[str, dict]:
    revenue, _ = revenue_series(context)
    breakdowns = {}
    for role in DIMENSION_ROLES:
        column = context.roles.get(role)
        if not column:
            continue
        labels = _group_labels(context.typed[column])
        frame = pd.DataFrame({"group": labels})
        aggregations = {"records": ("group", "size")}
        if revenue is not None:
            frame["revenue"] = revenue.values
            aggregations["revenue"] = ("revenue", "sum")
            aggregations["average_revenue"] = ("revenue", "mean")
        if context.roles.get("quantity"):
            frame["quantity"] = context.typed[context.roles["quantity"]].values
            aggregations["quantity"] = ("quantity", "sum")
        grouped = frame.groupby("group").agg(**aggregations)
        measure = "revenue" if revenue is not None else "records"
        grouped = grouped.sort_values(measure, ascending=False)
        total = grouped[measure].sum()
        rows = []
        for group, row in grouped.iterrows():
            rows.append(
                {
                    "group": str(group),
                    "records": int(row["records"]),
                    "revenue": _round(row["revenue"], 2) if "revenue" in row else None,
                    "average_revenue": _round(row["average_revenue"], 2) if "average_revenue" in row else None,
                    "quantity": _round(row["quantity"], 2) if "quantity" in row else None,
                    "share": _round(row[measure] / total * 100, 2) if total else None,
                }
            )
        breakdowns[role] = {
            "role": role,
            "column": column,
            "measure": measure,
            "rows": rows[:top_n],
            "total_groups": len(rows),
        }
    return breakdowns


def analyse(context: AnalysisContext) -> dict:
    """Run every applicable analysis and return a JSON-serialisable result."""
    metrics, notes = business_metrics(context)
    limitations = list(notes)
    revenue, revenue_source = revenue_series(context)

    trend = None
    comparison = None
    direction = None
    date_column = context.roles.get("date")
    if date_column:
        try:
            trend = time_series(context.typed[date_column], revenue, "sum" if revenue is not None else "count")
            if context.roles.get("quantity") is not None:
                quantity_series = time_series(
                    context.typed[date_column], context.typed[context.roles["quantity"]], "sum", trend["granularity"]
                )
                for point, quantity_point in zip(trend["points"], quantity_series["points"], strict=True):
                    point["quantity"] = quantity_point["value"]
            comparison = period_comparison(trend)
            direction = trend_direction(trend)
            if trend["excluded_rows"]:
                limitations.append(
                    f"{trend['excluded_rows']:,} rows without a readable date are excluded from time-based analysis."
                )
        except AnalysisError as error:
            limitations.append(str(error))
    else:
        limitations.append("No date column was found, so trends over time and period comparisons are unavailable.")

    breakdowns = dimension_breakdowns(context)
    if not breakdowns:
        limitations.append(
            "No category, product, region or status column was found, so group comparisons are limited to the visualisation builder."
        )

    distributions = {}
    if revenue is not None and revenue.notna().any():
        distributions["revenue"] = distribution(revenue)

    return {
        "roles": context.roles,
        "revenue_source": revenue_source,
        "metrics": metrics,
        "columns": column_summaries(context),
        "time_series": trend,
        "period_comparison": comparison,
        "trend": direction,
        "breakdowns": breakdowns,
        "distributions": distributions,
        "correlations": correlations(context),
        "limitations": limitations,
    }
