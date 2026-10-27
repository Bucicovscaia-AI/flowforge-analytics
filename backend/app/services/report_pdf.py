"""PDF business report built from the stored analysis results.

Every figure in the report comes from the analysis record (the same numbers
the dashboard shows). Nothing is typed in by hand.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

INK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")
ACCENT = colors.HexColor("#2a78d6")
LINE = colors.HexColor("#e2e8f0")
WARN_BG = colors.HexColor("#fef3c7")

LIMITATIONS = [
    "Revenue is calculated as quantity multiplied by unit price for each order line. Discounts, refunds, tax and shipping are not in the data and are not included.",
    "Rows that failed a cleaning rule are excluded from every KPI. The data-quality section shows how many were removed and why.",
    "Average order value counts each distinct order_id once, so an order with several lines is one order.",
    "Monthly figures use the order date. A first or last month that is only partly covered will look lower than a full month.",
    "Observations describe patterns in this dataset only. They do not establish causes and are not compared with any external benchmark.",
]


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], alignment=TA_LEFT, fontSize=20, leading=24, textColor=INK, spaceAfter=2),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontSize=10, textColor=MUTED, spaceAfter=10),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontSize=13, leading=16, textColor=INK, spaceBefore=12, spaceAfter=6),
        "body": ParagraphStyle("body", parent=base["Normal"], fontSize=9.5, leading=13, textColor=INK),
        "small": ParagraphStyle("small", parent=base["Normal"], fontSize=8.5, leading=11, textColor=MUTED),
        "cell": ParagraphStyle("cell", parent=base["Normal"], fontSize=8.5, leading=10.5, textColor=INK),
    }


def _gbp(value: float | None) -> str:
    return "Not available" if value is None else f"£{value:,.2f}"


def _num(value: float | int | None) -> str:
    return "Not available" if value is None else f"{value:,}"


def _table(rows: list[list], widths: list[float], header: bool = True) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        style += [("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("TEXTCOLOR", (0, 0), (-1, 0), MUTED)]
    table.setStyle(TableStyle(style))
    return table


def _bar_chart(title: str, rows: list[dict]) -> Drawing:
    rows = rows[:8]
    height = 40 + 18 * len(rows)
    drawing = Drawing(170 * mm, height)
    chart = HorizontalBarChart()
    chart.x, chart.y = 95, 10
    chart.width, chart.height = 170 * mm - 140, height - 35
    # Reverse so the largest bar is at the top.
    chart.data = [[r["revenue"] for r in reversed(rows)]]
    chart.categoryAxis.categoryNames = [r["name"][:22] for r in reversed(rows)]
    chart.categoryAxis.labels.fontSize = 8
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.valueMin = 0
    chart.valueAxis.labelTextFormat = lambda v: f"£{v / 1000:,.0f}k" if v >= 1000 else f"£{v:,.0f}"
    chart.bars[0].fillColor = ACCENT
    chart.bars[0].strokeColor = None
    drawing.add(chart)
    drawing.add(String(0, height - 12, title, fontSize=9, fontName="Helvetica-Bold", fillColor=INK))
    return drawing


def _line_chart(rows: list[dict]) -> Drawing:
    drawing = Drawing(170 * mm, 150)
    chart = HorizontalLineChart()
    chart.x, chart.y = 45, 25
    chart.width, chart.height = 170 * mm - 60, 100
    chart.data = [[r["revenue"] for r in rows]]
    chart.categoryAxis.categoryNames = [r["label"] for r in rows]
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.valueMin = 0
    chart.valueAxis.labelTextFormat = lambda v: f"£{v / 1000:,.0f}k" if v >= 1000 else f"£{v:,.0f}"
    chart.lines[0].strokeColor = ACCENT
    chart.lines[0].strokeWidth = 2
    drawing.add(chart)
    drawing.add(String(0, 138, "Revenue by month", fontSize=9, fontName="Helvetica-Bold", fillColor=INK))
    return drawing


def build_report_pdf(analysis: dict, title: str, insights: dict | None, generated_at: datetime) -> bytes:
    s = _styles()
    p = lambda text, style="body": Paragraph(escape(str(text)), s[style])  # noqa: E731
    dataset, quality, kpis = analysis["dataset"], analysis["quality"], analysis["kpis"]
    summary, breakdowns = kpis["summary"], kpis["breakdowns"]
    story: list = []

    story.append(p(title, "title"))
    story.append(p(f"FlowForge Analytics report · generated {generated_at:%d %B %Y, %H:%M} UTC · source file {dataset['file_name']}", "subtitle"))

    if dataset["synthetic"]:
        notice = Table(
            [[Paragraph(
                "<b>Synthetic data.</b> This report was produced from a fabricated demonstration dataset. "
                "The figures do not describe a real business and are not genuine business findings.",
                s["body"],
            )]],
            colWidths=[170 * mm],
        )
        notice.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), WARN_BG), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#f59e0b")), ("PADDING", (0, 0), (-1, -1), 6)]))
        story += [notice, Spacer(1, 6)]

    # 1. Dataset overview
    story.append(p("1. Dataset overview", "h2"))
    period = f"{summary.get('date_from', '?')} to {summary.get('date_to', '?')}" if summary.get("date_from") else "Not available"
    story.append(_table([
        ["File", dataset["file_name"]],
        ["Size", f"{dataset['size_bytes'] / 1024:,.1f} KB ({dataset['encoding']})"],
        ["Columns", Paragraph(escape(", ".join(dataset["columns"])), s["cell"])],
        ["Rows received", _num(quality["rows_received"])],
        ["Rows analysed", _num(quality["rows_analysed"])],
        ["Period covered", period],
        ["Analysed at", analysis["created_at"][:19].replace("T", " ") + " UTC"],
    ], [40 * mm, 130 * mm], header=False))

    # 2. Data quality
    story.append(p("2. Data-quality summary", "h2"))
    story.append(p(
        f"The file had {quality['duplicate_rows']:,} exact duplicate rows and {quality['missing_cells']:,} missing cells "
        f"({quality['completeness_pct']:.1f}% complete). The cleaning rules removed {quality['rows_removed']:,} rows, "
        f"leaving {quality['rows_analysed']:,} ({quality['quality_score']:.1f}% of the rows received)."
    ))
    story.append(Spacer(1, 4))
    rows = [["Rule", "Description", "Rows removed", "Cells changed"]]
    for step in analysis["cleaning_steps"]:
        rows.append([step["rule"], Paragraph(escape(step["description"]), s["cell"]), f"{step['rows_removed']:,}", f"{step['cells_changed']:,}"])
    story.append(_table(rows, [12 * mm, 108 * mm, 25 * mm, 25 * mm]))

    # 3. KPIs
    story.append(p("3. Key performance indicators", "h2"))
    story.append(_table([
        ["KPI", "Value"],
        ["Total revenue", _gbp(summary["total_revenue"])],
        ["Number of orders", _num(summary["order_count"])],
        ["Units sold", _num(summary["units_sold"])],
        ["Average order value", _gbp(summary["average_order_value"])],
        ["Order lines analysed", _num(summary["order_lines"])],
    ], [60 * mm, 110 * mm]))
    if kpis["unavailable"]:
        story.append(Spacer(1, 4))
        story.append(p(
            "Not available for this dataset: "
            + "; ".join(f"{u['label']} (needs {', '.join(u['missing_columns'])})" for u in kpis["unavailable"]),
            "small",
        ))

    if breakdowns.get("revenue_over_time"):
        story.append(Spacer(1, 6))
        story.append(_line_chart(breakdowns["revenue_over_time"]))
        rows = [["Month", "Revenue", "Orders", "Units"]] + [
            [m["label"], _gbp(m["revenue"]), _num(m["orders"]), _num(m["units"])] for m in breakdowns["revenue_over_time"]
        ]
        story.append(_table(rows, [40 * mm, 50 * mm, 40 * mm, 40 * mm]))

    for key, label in [("revenue_by_category", "Revenue by category"), ("revenue_by_region", "Revenue by region"), ("revenue_by_channel", "Revenue by channel")]:
        data = breakdowns.get(key)
        if not data:
            continue
        rows = [[label.split(" by ")[1].capitalize(), "Revenue", "Share", "Orders", "Avg order"]] + [
            [r["name"], _gbp(r["revenue"]), f"{r['share_pct']:.1f}%", _num(r["orders"]), _gbp(r["average_order_value"])] for r in data
        ]
        story.append(KeepTogether([Spacer(1, 8), _bar_chart(label, data), _table(rows, [50 * mm, 35 * mm, 25 * mm, 25 * mm, 35 * mm])]))

    # 4. Observations and recommendations
    story.append(p("4. Analytical observations and recommendations", "h2"))
    if insights and insights.get("source") == "ai":
        story.append(p(f"Source: AI-generated by {insights.get('model')} from the aggregated summary only. Check the evidence against the tables above.", "small"))
        if insights.get("summary"):
            story += [Spacer(1, 4), p(insights["summary"])]
    else:
        story.append(p("Source: rule-based observations calculated by FlowForge. These are not AI-generated.", "small"))
    items = (insights or {}).get("insights") or analysis["observations"]
    for i, item in enumerate(items, 1):
        story.append(Spacer(1, 5))
        story.append(KeepTogether([
            Paragraph(f"<b>{i}. {escape(item['title'])}</b>", s["body"]),
            Paragraph(f"<b>Evidence:</b> {escape(item['evidence'])}", s["body"]),
            Paragraph(f"<b>Recommendation:</b> {escape(item['recommendation'])}", s["body"]),
        ]))

    # 5. Limitations
    story.append(p("5. Limitations and assumptions", "h2"))
    limits = LIMITATIONS + [str(c) for c in (insights or {}).get("caveats", [])]
    if dataset["synthetic"]:
        limits.insert(0, "The dataset is synthetic. Results demonstrate the software and must not be read as real business performance.")
    for item in limits:
        story.append(Paragraph(f"• {escape(item)}", s["body"]))

    buffer = BytesIO()

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(20 * mm, 10 * mm, "FlowForge Analytics" + (" · synthetic demonstration data" if dataset["synthetic"] else ""))
        canvas.drawRightString(190 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm, title=title, author="FlowForge Analytics")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
