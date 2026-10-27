"""Rule-based analytical observations.

These are written by fixed rules from the calculated KPIs, not by an AI
model. They are always available, and they are the clearly labelled
fallback when the AI service is not configured or fails.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date


def _gbp(value: float) -> str:
    return f"£{value:,.0f}" if abs(value) >= 100 else f"£{value:,.2f}"


def _pct(value: float) -> str:
    return f"{value:.1f}%"


def build_observations(kpis: dict, quality: dict) -> list[dict]:
    summary = kpis["summary"]
    breakdowns = kpis["breakdowns"]
    out: list[dict] = []

    def add(kind: str, title: str, evidence: str, recommendation: str) -> None:
        out.append({"kind": kind, "title": title, "evidence": evidence, "recommendation": recommendation})

    months = breakdowns.get("revenue_over_time", [])
    if len(months) >= 2:
        first, last = months[0], months[-1]
        change = (last["revenue"] - first["revenue"]) / first["revenue"] * 100 if first["revenue"] else 0
        rises = sum(1 for a, b in zip(months, months[1:]) if b["revenue"] > a["revenue"])
        direction = "grew" if change > 5 else "fell" if change < -5 else "was broadly flat"
        add(
            "trend",
            f"Monthly revenue {direction} over the period",
            f"Revenue went from {_gbp(first['revenue'])} in {first['label']} to {_gbp(last['revenue'])} in "
            f"{last['label']} ({change:+.1f}%). Revenue rose in {rises} of the {len(months) - 1} month-on-month changes.",
            "Compare the same months in another year before treating this as a lasting trend.",
        )
        drops = [(b["revenue"] - a["revenue"]) / a["revenue"] * 100 if a["revenue"] else 0 for a, b in zip(months, months[1:])]
        worst = min(range(len(drops)), key=lambda i: drops[i])
        if drops[worst] < -5:
            add(
                "risk",
                f"Revenue dipped in {months[worst + 1]['label']}",
                f"Revenue fell {abs(drops[worst]):.1f}% from {months[worst]['label']} to {months[worst + 1]['label']}.",
                "Check promotions, stock levels and calendar effects in that month to explain the dip.",
            )
        # A final month that ends before its last day is only partly covered.
        end = date.fromisoformat(summary["date_to"]) if summary.get("date_to") else None
        if end and end.day < monthrange(end.year, end.month)[1]:
            add(
                "data",
                f"{last['label']} may be a partial month",
                f"The latest order is dated {end.isoformat()}, before the end of the month.",
                "Exclude or annualise the last month before comparing it with full months.",
            )

    for key, noun in [("revenue_by_category", "category"), ("revenue_by_region", "region"), ("revenue_by_channel", "channel")]:
        # "Unknown" is a placeholder from cleaning rule C8, not a real group.
        rows = [r for r in breakdowns.get(key) or [] if r["name"] != "Unknown"]
        if len(rows) < 2:
            continue
        top, bottom = rows[0], rows[-1]
        concentrated = top["share_pct"] >= 40
        add(
            "concentration" if concentrated else "mix",
            f"{top['name']} is the largest {noun}",
            f"{top['name']} produced {_gbp(top['revenue'])} ({_pct(top['share_pct'])} of revenue); "
            f"{bottom['name']} is smallest at {_pct(bottom['share_pct'])}.",
            f"Revenue depends heavily on one {noun}; review the risk if it under-performs."
            if concentrated
            else f"Look at what drives {bottom['name']}'s lower share before deciding whether to invest in it.",
        )

    regions = [r for r in breakdowns.get("revenue_by_region") or [] if r["name"] != "Unknown"]
    if len(regions) >= 2:
        by_aov = sorted(regions, key=lambda r: r["average_order_value"], reverse=True)
        hi, lo = by_aov[0], by_aov[-1]
        if lo["average_order_value"] and hi["average_order_value"] / lo["average_order_value"] > 1.1:
            add(
                "opportunity",
                "Average order value differs by region",
                f"{hi['name']} averages {_gbp(hi['average_order_value'])} per order against "
                f"{_gbp(lo['average_order_value'])} in {lo['name']}.",
                f"Test bundles or upselling in {lo['name']} to close part of the gap.",
            )

    products = breakdowns.get("top_products") or []
    if products:
        p = products[0]
        add(
            "mix",
            f"{p['name']} is the best-selling product by revenue",
            f"{p['name']} generated {_gbp(p['revenue'])} from {p['units']:,} units ({_pct(p['share_pct'])} of revenue).",
            "Keep stock cover for this product under review.",
        )

    removed = quality.get("rows_removed", 0)
    received = quality.get("rows_received", 0)
    if received:
        share = removed / received * 100
        add(
            "data",
            "Data quality" + (" needs attention" if share > 5 else " is good"),
            f"{removed:,} of {received:,} rows ({_pct(share)}) were removed by the cleaning rules; "
            f"{quality.get('duplicate_rows', 0):,} were exact duplicates.",
            "Fix the issues at source (the export or entry form) so fewer rows are lost."
            if removed
            else "No action needed.",
        )

    for item in kpis.get("unavailable", []):
        add(
            "data",
            f"{item['label']} could not be calculated",
            f"The dataset has no {', '.join(item['missing_columns'])} column.",
            f"Include {', '.join(item['missing_columns'])} in the export to unlock this analysis.",
        )

    return out
