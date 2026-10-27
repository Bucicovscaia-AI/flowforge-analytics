"""KPI calculations on the cleaned dataset.

Each KPI declares the columns it needs. A KPI whose columns are missing is
not guessed: it is listed under ``unavailable`` with the reason, and the
interface and report show it as "not available".
"""

from __future__ import annotations

import pandas as pd

KPI_REQUIREMENTS: dict[str, list[str]] = {
    "total_revenue": ["quantity", "unit_price"],
    "order_count": ["order_id"],
    "units_sold": ["quantity"],
    "average_order_value": ["order_id", "quantity", "unit_price"],
    "revenue_over_time": ["order_date", "quantity", "unit_price"],
    "revenue_by_category": ["product_category", "quantity", "unit_price"],
    "revenue_by_region": ["region", "quantity", "unit_price"],
    "revenue_by_channel": ["channel", "quantity", "unit_price"],
    "revenue_by_customer_type": ["customer_type", "quantity", "unit_price"],
    "top_products": ["product", "quantity", "unit_price"],
}

KPI_LABELS = {
    "total_revenue": "Total revenue",
    "order_count": "Number of orders",
    "units_sold": "Units sold",
    "average_order_value": "Average order value",
    "revenue_over_time": "Revenue over time",
    "revenue_by_category": "Revenue by category",
    "revenue_by_region": "Revenue by region",
    "revenue_by_channel": "Revenue by channel",
    "revenue_by_customer_type": "Revenue by customer type",
    "top_products": "Top products",
}


def missing_columns(frame: pd.DataFrame, kpi: str) -> list[str]:
    return [c for c in KPI_REQUIREMENTS[kpi] if c not in frame.columns]


def _breakdown(df: pd.DataFrame, column: str, total: float, limit: int | None = None) -> list[dict]:
    grouped = (
        df.groupby(column, observed=True)
        .agg(revenue=("revenue", "sum"), orders=("order_id", "nunique") if "order_id" in df else ("revenue", "size"), units=("quantity", "sum"))
        .sort_values("revenue", ascending=False)
    )
    if limit:
        grouped = grouped.head(limit)
    return [
        {
            "name": str(name),
            "revenue": round(float(row.revenue), 2),
            "orders": int(row.orders),
            "units": int(row.units),
            "share_pct": round(float(row.revenue) / total * 100, 2) if total else 0.0,
            "average_order_value": round(float(row.revenue) / row.orders, 2) if row.orders else 0.0,
        }
        for name, row in grouped.iterrows()
    ]


def _monthly(df: pd.DataFrame) -> list[dict]:
    months = df.assign(month=df["order_date"].dt.to_period("M"))
    agg = {"revenue": ("revenue", "sum"), "units": ("quantity", "sum")}
    if "order_id" in df:
        agg["orders"] = ("order_id", "nunique")
    grouped = months.groupby("month").agg(**agg).sort_index()
    out = []
    for period, row in grouped.iterrows():
        out.append(
            {
                "period": str(period),
                "label": period.strftime("%b %Y"),
                "revenue": round(float(row.revenue), 2),
                "units": int(row.units),
                "orders": int(row["orders"]) if "orders" in row else None,
            }
        )
    return out


def calculate_kpis(df: pd.DataFrame) -> dict:
    """Return scalar KPIs, breakdowns and the list of unavailable KPIs."""
    unavailable = []
    for kpi in KPI_REQUIREMENTS:
        cols = missing_columns(df, kpi)
        if cols:
            unavailable.append({"kpi": kpi, "label": KPI_LABELS[kpi], "missing_columns": cols})
    skip = {u["kpi"] for u in unavailable}

    total_revenue = round(float(df["revenue"].sum()), 2) if "total_revenue" not in skip else None
    order_count = int(df["order_id"].nunique()) if "order_count" not in skip else None
    units_sold = int(df["quantity"].sum()) if "units_sold" not in skip else None
    aov = None
    if "average_order_value" not in skip and order_count:
        aov = round(total_revenue / order_count, 2)

    summary = {
        "total_revenue": total_revenue,
        "order_count": order_count,
        "units_sold": units_sold,
        "average_order_value": aov,
        "order_lines": int(len(df)),
        "average_units_per_order": round(units_sold / order_count, 2) if order_count and units_sold is not None else None,
        "currency": "GBP",
    }
    if len(df) and "order_date" in df:
        summary["date_from"] = df["order_date"].min().date().isoformat()
        summary["date_to"] = df["order_date"].max().date().isoformat()

    total = total_revenue or 0.0
    breakdowns: dict[str, list[dict]] = {}
    if "revenue_over_time" not in skip and len(df):
        breakdowns["revenue_over_time"] = _monthly(df)
    for kpi, column, limit in [
        ("revenue_by_category", "product_category", None),
        ("revenue_by_region", "region", None),
        ("revenue_by_channel", "channel", None),
        ("revenue_by_customer_type", "customer_type", None),
        ("top_products", "product", 10),
    ]:
        if kpi not in skip and len(df):
            breakdowns[kpi] = _breakdown(df, column, total, limit)

    return {"summary": summary, "breakdowns": breakdowns, "unavailable": unavailable}
