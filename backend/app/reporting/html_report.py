"""Render a report document as a self-contained HTML page.

All text from datasets (column names, category labels, insight text) is
escaped before it is written into the page. Charts are inline SVG so the file
works offline and can be printed to PDF from a browser.
"""

from __future__ import annotations

from html import escape

from app.reporting.document import (
    INSIGHT_SOURCE_LABELS,
    KIND_LABELS,
    ROLE_TITLES,
    format_metric,
    format_value,
)

BRAND = "#2a78d6"
INK = "#0f172a"
MUTED = "#64748b"
GRID = "#e2e8f0"

STYLES = f"""
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: Inter, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: {INK}; background: #f8fafc; line-height: 1.5; }}
main {{ max-width: 960px; margin: 0 auto; padding: 40px 24px 64px; }}
header.report {{ border-bottom: 3px solid {BRAND}; padding-bottom: 20px; margin-bottom: 28px; }}
.brand {{ font-weight: 700; letter-spacing: -0.01em; color: {BRAND}; font-size: 14px; text-transform: uppercase; }}
h1 {{ font-size: 28px; margin: 8px 0 4px; letter-spacing: -0.02em; }}
h2 {{ font-size: 18px; margin: 36px 0 12px; padding-bottom: 6px; border-bottom: 1px solid {GRID}; }}
h3 {{ font-size: 15px; margin: 20px 0 8px; }}
.meta {{ color: {MUTED}; font-size: 14px; }}
.notice {{ background: #fff7ed; border: 1px solid #fed7aa; color: #9a3412; padding: 10px 14px; border-radius: 8px; font-size: 14px; margin: 12px 0; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }}
.card {{ background: #fff; border: 1px solid {GRID}; border-radius: 10px; padding: 14px 16px; }}
.card .label {{ color: {MUTED}; font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }}
.card .value {{ font-size: 22px; font-weight: 650; margin-top: 4px; font-variant-numeric: tabular-nums; }}
.card .hint {{ color: {MUTED}; font-size: 12px; margin-top: 4px; }}
table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid {GRID}; border-radius: 10px; overflow: hidden; font-size: 13px; }}
th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid {GRID}; vertical-align: top; }}
th {{ background: #f1f5f9; font-weight: 600; color: #334155; }}
td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.badge {{ display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 999px; }}
.sev-error {{ background: #fee2e2; color: #991b1b; }}
.sev-warning {{ background: #fef3c7; color: #92400e; }}
.sev-info {{ background: #e0f2fe; color: #075985; }}
.kind {{ background: #eef2ff; color: #3730a3; }}
.source {{ background: #f1f5f9; color: #334155; }}
.insight {{ background: #fff; border: 1px solid {GRID}; border-radius: 10px; padding: 14px 16px; margin-bottom: 10px; }}
.insight h4 {{ margin: 6px 0 4px; font-size: 15px; }}
.insight p {{ margin: 4px 0; font-size: 14px; }}
.evidence {{ color: {MUTED}; font-size: 13px; }}
.caveat {{ color: #92400e; font-size: 13px; }}
.chart {{ background: #fff; border: 1px solid {GRID}; border-radius: 10px; padding: 12px; margin-bottom: 12px; }}
.chart svg {{ width: 100%; height: auto; display: block; }}
ul {{ padding-left: 20px; }}
footer {{ color: {MUTED}; font-size: 12px; margin-top: 48px; border-top: 1px solid {GRID}; padding-top: 12px; }}
@media print {{ body {{ background: #fff; }} main {{ padding: 0; }} .card, .chart, .insight, table {{ break-inside: avoid; }} }}
"""


def _e(value) -> str:
    return escape("" if value is None else str(value))


def _short(text: str, limit: int = 18) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def bar_chart_svg(rows: list[dict], value_key: str, title: str) -> str:
    rows = [row for row in rows if row.get(value_key) is not None][:10]
    if not rows:
        return ""
    width, row_height, label_width, value_width = 720, 26, 170, 90
    height = row_height * len(rows) + 10
    maximum = max(row[value_key] for row in rows) or 1
    plot = width - label_width - value_width
    bars = []
    for index, row in enumerate(rows):
        y = index * row_height + 5
        length = max(2, plot * row[value_key] / maximum) if row[value_key] > 0 else 0
        bars.append(
            f'<text x="{label_width - 8}" y="{y + 16}" text-anchor="end" font-size="12" fill="{INK}">{_e(_short(row["group"], 24))}</text>'
            f'<rect x="{label_width}" y="{y + 4}" width="{length:.1f}" height="16" rx="3" fill="{BRAND}"/>'
            f'<text x="{label_width + length + 6:.1f}" y="{y + 16}" font-size="12" fill="{MUTED}">{_e(format_value(row[value_key], "number"))}</text>'
        )
    return (
        f'<div class="chart"><h3>{_e(title)}</h3>'
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{_e(title)}">{"".join(bars)}</svg></div>'
    )


def line_chart_svg(points: list[dict], title: str, y_label: str) -> str:
    points = [point for point in points if point.get("value") is not None]
    if len(points) < 2:
        return ""
    width, height, left, right, top, bottom = 720, 260, 70, 20, 16, 44
    plot_w, plot_h = width - left - right, height - top - bottom
    maximum = max(point["value"] for point in points)
    minimum = min(0, min(point["value"] for point in points))
    span = (maximum - minimum) or 1
    step = plot_w / (len(points) - 1)

    def y_of(value: float) -> float:
        return top + plot_h - (value - minimum) / span * plot_h

    grid = []
    for fraction in (0, 0.25, 0.5, 0.75, 1):
        value = minimum + span * fraction
        y = y_of(value)
        grid.append(
            f'<line x1="{left}" x2="{width - right}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>'
            f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{MUTED}">{_e(format_value(round(value), "integer"))}</text>'
        )
    coordinates = " ".join(f"{left + index * step:.1f},{y_of(point['value']):.1f}" for index, point in enumerate(points))
    label_every = max(1, len(points) // 8)
    labels = "".join(
        f'<text x="{left + index * step:.1f}" y="{height - 22}" text-anchor="middle" font-size="11" fill="{MUTED}">{_e(_short(point["label"].replace("Week of ", ""), 12))}</text>'
        for index, point in enumerate(points)
        if index % label_every == 0
    )
    markers = "".join(
        f'<circle cx="{left + index * step:.1f}" cy="{y_of(point["value"]):.1f}" r="3" fill="{BRAND}"><title>{_e(point["label"])}: {_e(format_value(point["value"], "number"))}</title></circle>'
        for index, point in enumerate(points)
    )
    axis_label = f'<text x="{left}" y="{height - 4}" font-size="11" fill="{MUTED}">{_e(y_label)} by period</text>'
    return (
        f'<div class="chart"><h3>{_e(title)}</h3><svg viewBox="0 0 {width} {height}" role="img" aria-label="{_e(title)}">'
        f'{"".join(grid)}<polyline points="{coordinates}" fill="none" stroke="{BRAND}" stroke-width="2"/>{markers}{labels}{axis_label}</svg></div>'
    )


def _metrics_section(document: dict) -> str:
    cards = "".join(
        f'<div class="card"><div class="label">{_e(metric["label"])}</div><div class="value">{_e(format_metric(metric))}</div>'
        f'<div class="hint">{_e(metric.get("description", ""))}</div></div>'
        for metric in document["metrics"]
    )
    return f'<section><h2>Key metrics</h2><div class="grid">{cards}</div></section>'


def _quality_section(document: dict) -> str:
    quality = document["quality"]
    rows = (
        "".join(
            f'<tr><td><span class="badge sev-{_e(finding["severity"])}">{_e(finding["severity"].title())}</span></td>'
            f'<td>{_e(finding["title"])}<div class="evidence">{_e(finding["description"])}</div></td>'
            f'<td class="num">{finding["affected_rows"]:,}</td></tr>'
            for finding in quality["findings"]
        )
        or '<tr><td colspan="3">No data quality issues were detected by the configured checks.</td></tr>'
    )
    return (
        "<section><h2>Data quality</h2>"
        f'<div class="grid"><div class="card"><div class="label">Quality score</div><div class="value">{quality["score"]}</div><div class="hint">{_e(quality["grade"])}</div></div>'
        f'<div class="card"><div class="label">Missing cells</div><div class="value">{quality["missing_cells"]:,}</div></div>'
        f'<div class="card"><div class="label">Duplicate rows</div><div class="value">{quality["duplicate_rows"]:,}</div></div></div>'
        f'<p class="meta">{_e(quality["method"])}</p>'
        f'<table><thead><tr><th>Severity</th><th>Finding</th><th class="num">Rows affected</th></tr></thead><tbody>{rows}</tbody></table></section>'
    )


def _trend_section(document: dict) -> str:
    series = document.get("time_series")
    if not series:
        return ""
    measure = "Revenue" if series["aggregation"] == "sum" else "Records"
    parts = [line_chart_svg(series["points"], f"{measure} by {series['granularity']}", measure)]
    comparison = document.get("period_comparison")
    if comparison:
        change = comparison["change_percent"]
        parts.append(
            f"<p>{_e(comparison['current']['label'])}: <strong>{_e(format_value(comparison['current']['value'], 'number'))}</strong> compared with "
            f"{_e(comparison['previous']['label'])}: <strong>{_e(format_value(comparison['previous']['value'], 'number'))}</strong>"
            + (f" ({change:+.1f}%)." if change is not None else ".")
            + "</p>"
        )
        if comparison.get("note"):
            parts.append(f'<p class="meta">{_e(comparison["note"])}</p>')
    partial = [point["label"] for point in series["points"] if point["partial"]]
    if partial:
        parts.append(f'<p class="meta">Periods with partial data: {_e(", ".join(partial))}.</p>')
    return "<section><h2>Trends over time</h2>" + "".join(parts) + "</section>"


def _breakdown_section(document: dict) -> str:
    parts = []
    for role, breakdown in document.get("breakdowns", {}).items():
        measure = breakdown["measure"]
        title = f"{ROLE_TITLES.get(role, role.title())}: {measure} by '{breakdown['column']}'"
        parts.append(bar_chart_svg(breakdown["rows"], measure, title))
        rows = "".join(
            f'<tr><td>{_e(row["group"])}</td><td class="num">{row["records"]:,}</td>'
            f'<td class="num">{_e(format_value(row.get("revenue"), "currency"))}</td>'
            f'<td class="num">{_e(format_value(row.get("share"), "percent"))}</td></tr>'
            for row in breakdown["rows"][:10]
        )
        more = f'<p class="meta">Showing 10 of {breakdown["total_groups"]} groups.</p>' if breakdown["total_groups"] > 10 else ""
        parts.append(
            f'<table><thead><tr><th>{_e(breakdown["column"])}</th><th class="num">Records</th><th class="num">Revenue</th>'
            f'<th class="num">Share</th></tr></thead><tbody>{rows}</tbody></table>{more}'
        )
    if not parts:
        return ""
    return "<section><h2>Comparisons</h2>" + "".join(parts) + "</section>"


def _insights_section(document: dict) -> str:
    insights = document["insights"]
    mode = "AI-assisted" if insights["mode"] == "ai" else "Rule-based"
    provider = f" ({_e(insights['provider'])}, {_e(insights['model'])})" if insights.get("provider") else ""
    notices = "".join(f'<div class="notice">{_e(notice)}</div>' for notice in insights.get("notices", []))
    items = []
    for item in insights["items"]:
        evidence = "; ".join(f"{entry['label']}: {entry['value']}" for entry in item.get("evidence", []))
        items.append(
            '<div class="insight">'
            f'<span class="badge source">{_e(INSIGHT_SOURCE_LABELS.get(item["source"], item["source"]))}</span> '
            f'<span class="badge kind">{_e(KIND_LABELS.get(item["kind"], item["kind"]))}</span>'
            f"<h4>{_e(item['title'])}</h4><p>{_e(item['statement'])}</p>"
            + (f'<p class="evidence">Evidence: {_e(evidence)}</p>' if evidence else "")
            + (f'<p class="caveat">Caveat: {_e(item["caveat"])}</p>' if item.get("caveat") else "")
            + "</div>"
        )
    body = "".join(items) or "<p>No insights could be derived from this dataset.</p>"
    return f'<section><h2>Insights</h2><p class="meta">Mode: {mode}{provider}</p>{notices}{body}</section>'


def render_html(document: dict) -> str:
    dataset = document["dataset"]
    scope = document["scope"]
    sample_notice = (
        '<div class="notice">This report is based on synthetic demonstration data, not real business records.</div>'
        if dataset["is_sample"]
        else ""
    )
    cleaning = (
        "<h3>Cleaning applied before analysis</h3><ul>"
        + "".join(f"<li>{_e(step)}</li>" for step in scope["cleaning_steps"])
        + "</ul>"
        if scope["cleaning_steps"]
        else "<p>No cleaning operations were applied to this dataset.</p>"
    )
    limitations = "".join(f"<li>{_e(item)}</li>" for item in document["limitations"])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(document["title"])}</title>
<style>{STYLES}</style>
</head>
<body>
<main>
<header class="report">
<div class="brand">FlowForge Analytics</div>
<h1>{_e(document["title"])}</h1>
<div class="meta">Generated {_e(document["generated_at"].replace("T", " ").replace("+00:00", " UTC"))} · Dataset: {_e(dataset["name"])} · {dataset["record_count"]:,} records · Status: {_e(document["status"])}</div>
</header>
{sample_notice}
<section><h2>Scope</h2><p>{_e(scope["description"])}</p>{cleaning}</section>
{_metrics_section(document)}
{_trend_section(document)}
{_breakdown_section(document)}
{_quality_section(document)}
{_insights_section(document)}
<section><h2>Limitations</h2><ul>{limitations}</ul></section>
<footer>Report {_e(document["id"])} · Produced by FlowForge Analytics from the dataset's calculated results.</footer>
</main>
</body>
</html>
"""
