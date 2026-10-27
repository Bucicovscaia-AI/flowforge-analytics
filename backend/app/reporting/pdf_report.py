"""Render a report document as a PDF using ReportLab."""

from __future__ import annotations

import io
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.reporting.document import (
    INSIGHT_SOURCE_LABELS,
    KIND_LABELS,
    ROLE_TITLES,
    format_metric,
    format_value,
)

BRAND = colors.HexColor("#2a78d6")
INK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")
GRID = colors.HexColor("#e2e8f0")
HEADER_BG = colors.HexColor("#f1f5f9")

# The built-in PDF fonts cover Windows-1252 only; map common symbols outside it.
_REPLACEMENTS = {"−": "-", "÷": "/", "≥": ">=", "≤": "<=", "→": "->", "…": "...", "–": "-"}


def _plain(value) -> str:
    """Text for table cells and drawings, which ReportLab does not parse as markup."""
    text = "" if value is None else str(value)
    for original, replacement in _REPLACEMENTS.items():
        text = text.replace(original, replacement)
    return text.encode("cp1252", errors="replace").decode("cp1252")


def _text(value) -> str:
    """Text for Paragraphs, which ReportLab parses as markup, so it must be escaped."""
    return escape(_plain(value))


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle("brand", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=BRAND),
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            alignment=TA_LEFT,
            textColor=INK,
            spaceAfter=4,
        ),
        "meta": ParagraphStyle("meta", parent=base["Normal"], fontSize=8.5, leading=11, textColor=MUTED),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=INK,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "h3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13,
            textColor=INK,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle("body", parent=base["Normal"], fontSize=9.5, leading=13, textColor=INK),
        "small": ParagraphStyle("small", parent=base["Normal"], fontSize=8.5, leading=11, textColor=MUTED),
        "cell": ParagraphStyle("cell", parent=base["Normal"], fontSize=8.5, leading=10.5, textColor=INK),
        "notice": ParagraphStyle(
            "notice",
            parent=base["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#9a3412"),
            backColor=colors.HexColor("#fff7ed"),
            borderPadding=6,
            spaceBefore=4,
            spaceAfter=8,
        ),
    }


def _table(rows: list[list], widths: list[float], numeric_columns: tuple[int, ...] = ()) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1)
    style = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, GRID),
        ("BOX", (0, 0), (-1, -1), 0.5, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for column in numeric_columns:
        style.append(("ALIGN", (column, 0), (column, -1), "RIGHT"))
    table.setStyle(TableStyle(style))
    return table


def _bar_chart(rows: list[dict], value_key: str, title: str) -> Drawing | None:
    rows = [row for row in rows if row.get(value_key) is not None][:8]
    if not rows:
        return None
    rows = list(reversed(rows))
    height = 30 + 18 * len(rows)
    drawing = Drawing(170 * mm, height)
    chart = HorizontalBarChart()
    chart.x, chart.y = 95, 10
    chart.width, chart.height = 170 * mm - 120, height - 30
    chart.data = [[row[value_key] for row in rows]]
    chart.categoryAxis.categoryNames = [_plain(row["group"])[:28] for row in rows]
    chart.categoryAxis.labels.fontSize = 7.5
    chart.categoryAxis.labels.boxAnchor = "e"
    chart.categoryAxis.labels.fillColor = INK
    chart.valueAxis.valueMin = 0
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labels.fillColor = MUTED
    chart.valueAxis.gridStrokeColor = GRID
    chart.valueAxis.visibleGrid = True
    chart.bars[0].fillColor = BRAND
    chart.bars[0].strokeColor = None
    drawing.add(chart)
    drawing.add(String(0, height - 10, _plain(title), fontName="Helvetica-Bold", fontSize=9, fillColor=INK))
    return drawing


def _line_chart(points: list[dict], title: str) -> Drawing | None:
    points = [point for point in points if point.get("value") is not None]
    if len(points) < 2:
        return None
    drawing = Drawing(170 * mm, 70 * mm)
    chart = HorizontalLineChart()
    chart.x, chart.y = 45, 25
    chart.width, chart.height = 170 * mm - 60, 70 * mm - 50
    chart.data = [[point["value"] for point in points]]
    step = max(1, len(points) // 8)
    chart.categoryAxis.categoryNames = [
        point["label"].replace("Week of ", "") if index % step == 0 else "" for index, point in enumerate(points)
    ]
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.fillColor = MUTED
    chart.valueAxis.valueMin = 0
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labels.fillColor = MUTED
    chart.valueAxis.gridStrokeColor = GRID
    chart.valueAxis.visibleGrid = True
    chart.lines[0].strokeColor = BRAND
    chart.lines[0].strokeWidth = 1.6
    drawing.add(chart)
    drawing.add(String(0, 70 * mm - 10, _plain(title), fontName="Helvetica-Bold", fontSize=9, fillColor=INK))
    return drawing


def _footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 10 * mm, "FlowForge Analytics")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {document.page}")
    canvas.restoreState()


def render_pdf(document: dict) -> bytes:
    styles = _styles()
    buffer = io.BytesIO()
    pdf = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=document["title"],
        author="FlowForge Analytics",
    )
    width = A4[0] - 36 * mm
    dataset = document["dataset"]
    story: list = [
        Paragraph("FLOWFORGE ANALYTICS", styles["brand"]),
        Paragraph(_text(document["title"]), styles["title"]),
        Paragraph(
            _text(
                f"Generated {document['generated_at'].replace('T', ' ').replace('+00:00', ' UTC')} · "
                f"Dataset: {dataset['name']} · {dataset['record_count']:,} records · Status: {document['status']}"
            ),
            styles["meta"],
        ),
        Spacer(1, 6),
    ]
    if dataset["is_sample"]:
        story.append(
            Paragraph("This report is based on synthetic demonstration data, not real business records.", styles["notice"])
        )

    story.append(Paragraph("Scope", styles["h2"]))
    story.append(Paragraph(_text(document["scope"]["description"]), styles["body"]))
    steps = document["scope"]["cleaning_steps"]
    story.append(
        Paragraph(
            _text("Cleaning applied: " + "; ".join(steps)) if steps else "No cleaning operations were applied.", styles["small"]
        )
    )

    story.append(Paragraph("Key metrics", styles["h2"]))
    metric_rows = [["Metric", "Value", "Definition"]] + [
        [
            Paragraph(_text(metric["label"]), styles["cell"]),
            _plain(format_metric(metric)),
            Paragraph(_text(metric.get("description", "")), styles["cell"]),
        ]
        for metric in document["metrics"]
    ]
    story.append(_table(metric_rows, [45 * mm, 35 * mm, width - 80 * mm], numeric_columns=(1,)))

    series = document.get("time_series")
    if series:
        story.append(Paragraph("Trends over time", styles["h2"]))
        measure = "Revenue" if series["aggregation"] == "sum" else "Records"
        chart = _line_chart(series["points"], f"{measure} by {series['granularity']}")
        if chart:
            story.append(chart)
        comparison = document.get("period_comparison")
        if comparison:
            change = comparison["change_percent"]
            story.append(
                Paragraph(
                    _text(
                        f"{comparison['current']['label']}: {format_value(comparison['current']['value'], 'number')} compared with "
                        f"{comparison['previous']['label']}: {format_value(comparison['previous']['value'], 'number')}"
                        + (f" ({change:+.1f}%)." if change is not None else ".")
                        + (f" {comparison['note']}" if comparison.get("note") else "")
                    ),
                    styles["body"],
                )
            )

    breakdowns = document.get("breakdowns", {})
    if breakdowns:
        story.append(Paragraph("Comparisons", styles["h2"]))
        for role, breakdown in breakdowns.items():
            measure = breakdown["measure"]
            title = f"{ROLE_TITLES.get(role, role.title())}: {measure} by '{breakdown['column']}'"
            chart = _bar_chart(breakdown["rows"], measure, title)
            rows = [[_plain(breakdown["column"]), "Records", "Revenue", "Share"]] + [
                [
                    Paragraph(_text(row["group"]), styles["cell"]),
                    f"{row['records']:,}",
                    format_value(row.get("revenue"), "currency"),
                    format_value(row.get("share"), "percent"),
                ]
                for row in breakdown["rows"][:10]
            ]
            block = [chart] if chart else []
            block.append(_table(rows, [width - 90 * mm, 25 * mm, 40 * mm, 25 * mm], numeric_columns=(1, 2, 3)))
            if breakdown["total_groups"] > 10:
                block.append(Paragraph(f"Showing 10 of {breakdown['total_groups']} groups.", styles["small"]))
            block.append(Spacer(1, 8))
            story.append(KeepTogether(block))

    quality = document["quality"]
    story.append(Paragraph("Data quality", styles["h2"]))
    story.append(
        Paragraph(
            _text(
                f"Quality score {quality['score']} ({quality['grade']}). Missing cells: {quality['missing_cells']:,}. "
                f"Duplicate rows: {quality['duplicate_rows']:,}."
            ),
            styles["body"],
        )
    )
    story.append(Paragraph(_text(quality["method"]), styles["small"]))
    if quality["findings"]:
        finding_rows = [["Severity", "Finding", "Rows"]] + [
            [
                finding["severity"].title(),
                Paragraph(_text(f"{finding['title']}. {finding['description']}"), styles["cell"]),
                f"{finding['affected_rows']:,}",
            ]
            for finding in quality["findings"]
        ]
        story.append(Spacer(1, 4))
        story.append(_table(finding_rows, [20 * mm, width - 40 * mm, 20 * mm], numeric_columns=(2,)))
    else:
        story.append(Paragraph("No data quality issues were detected by the configured checks.", styles["body"]))

    insights = document["insights"]
    story.append(Paragraph("Insights", styles["h2"]))
    mode = "AI-assisted" if insights["mode"] == "ai" else "Rule-based"
    provider = f" ({insights['provider']}, {insights['model']})" if insights.get("provider") else ""
    story.append(Paragraph(_text(f"Mode: {mode}{provider}"), styles["small"]))
    for notice in insights.get("notices", []):
        story.append(Paragraph(_text(notice), styles["notice"]))
    for item in insights["items"]:
        label = f"{INSIGHT_SOURCE_LABELS.get(item['source'], item['source'])} · {KIND_LABELS.get(item['kind'], item['kind'])}"
        block = [
            Paragraph(_text(label.upper()), styles["small"]),
            Paragraph(f"<b>{_text(item['title'])}</b>", styles["body"]),
            Paragraph(_text(item["statement"]), styles["body"]),
        ]
        evidence = "; ".join(f"{entry['label']}: {entry['value']}" for entry in item.get("evidence", []))
        if evidence:
            block.append(Paragraph(_text(f"Evidence: {evidence}"), styles["small"]))
        if item.get("caveat"):
            block.append(Paragraph(_text(f"Caveat: {item['caveat']}"), styles["small"]))
        block.append(Spacer(1, 6))
        story.append(KeepTogether(block))
    if not insights["items"]:
        story.append(Paragraph("No insights could be derived from this dataset.", styles["body"]))

    story.append(Paragraph("Limitations", styles["h2"]))
    for item in document["limitations"]:
        story.append(Paragraph(_text(f"• {item}"), styles["body"]))

    pdf.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
