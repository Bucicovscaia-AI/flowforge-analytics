"""Rule-based insights derived from analysis and data quality results.

Every insight is built from figures already calculated by the analytics and
quality engines. Each one is labelled as a measured fact, an interpretation
or a suggestion, and carries the evidence it is based on. When a rule's
conditions are not met it produces nothing rather than a filler statement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

FACT = "fact"
INTERPRETATION = "interpretation"
SUGGESTION = "suggestion"

_NEGATIVE_STATUS_WORDS = ("cancel", "return", "refund", "fail", "reject", "void")


@dataclass
class Evidence:
    label: str
    value: str


@dataclass
class Insight:
    id: str
    category: str
    kind: str
    title: str
    statement: str
    evidence: list[Evidence] = field(default_factory=list)
    caveat: str | None = None
    source: str = "rule_based"

    def to_dict(self) -> dict:
        return asdict(self)


def _money(value: float | None) -> str:
    return "n/a" if value is None else f"{value:,.2f}"


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f}%"


def _metric(analysis: dict, key: str):
    return next((metric for metric in analysis.get("metrics", []) if metric["key"] == key), None)


def _measure_name(breakdown: dict) -> str:
    return "revenue" if breakdown["measure"] == "revenue" else "records"


def _top_group_insights(analysis: dict) -> list[Insight]:
    insights = []
    for role in ("category", "region", "product"):
        breakdown = analysis.get("breakdowns", {}).get(role)
        if not breakdown or breakdown["total_groups"] < 2:
            continue
        rows = [row for row in breakdown["rows"] if row["group"] != "(missing)"]
        if len(rows) < 2:
            continue
        top, bottom = rows[0], rows[-1]
        measure = _measure_name(breakdown)
        column = breakdown["column"]
        value_key = "revenue" if measure == "revenue" else "records"
        evidence = [
            Evidence(f"{top['group']} {measure}", _money(top[value_key]) if measure == "revenue" else f"{top['records']:,}"),
            Evidence("Share of total", _pct(top["share"])),
            Evidence(f"Groups in '{column}'", str(breakdown["total_groups"])),
        ]
        insights.append(
            Insight(
                id=f"top-{role}",
                category="performance",
                kind=FACT,
                title=f"{top['group']} leads by {measure}",
                statement=f"'{top['group']}' accounts for {_pct(top['share'])} of total {measure} across {breakdown['total_groups']} values of '{column}'.",
                evidence=evidence,
            )
        )
        if role != "product" and top["share"] is not None and top["share"] >= 50:
            insights.append(
                Insight(
                    id=f"concentration-{role}",
                    category="composition",
                    kind=INTERPRETATION,
                    title=f"{measure.title()} is concentrated in one {role}",
                    statement=f"More than half of {measure} comes from '{top['group']}', so results for the whole dataset are heavily influenced by this one {role}.",
                    evidence=[Evidence("Share", _pct(top["share"]))],
                    caveat="Concentration describes the data as recorded; it does not by itself indicate risk or opportunity.",
                )
            )
        if (
            role != "product"
            and breakdown["total_groups"] == len(breakdown["rows"])
            and top[value_key]
            and bottom[value_key]
            and bottom[value_key] > 0
        ):
            ratio = top[value_key] / bottom[value_key]
            if ratio >= 1.5:
                insights.append(
                    Insight(
                        id=f"spread-{role}",
                        category="performance",
                        kind=FACT,
                        title=f"Wide gap between {role} results",
                        statement=f"'{top['group']}' has {ratio:.1f}× the {measure} of '{bottom['group']}', the lowest {role}.",
                        evidence=[
                            Evidence(top["group"], _money(top[value_key]) if measure == "revenue" else str(top["records"])),
                            Evidence(
                                bottom["group"], _money(bottom[value_key]) if measure == "revenue" else str(bottom["records"])
                            ),
                        ],
                        caveat="Differences in group size (number of records) can explain much of the gap.",
                    )
                )
    product = analysis.get("breakdowns", {}).get("product")
    if product and product["measure"] == "revenue" and product["total_groups"] >= 10:
        top_five = sum(row["share"] or 0 for row in product["rows"][:5])
        insights.append(
            Insight(
                id="product-top-five",
                category="composition",
                kind=FACT,
                title="Top five products' share of revenue",
                statement=f"The five highest-revenue products generate {_pct(top_five)} of revenue out of {product['total_groups']} products.",
                evidence=[Evidence(row["group"], _pct(row["share"])) for row in product["rows"][:5]],
            )
        )
    return insights


def _trend_insights(analysis: dict) -> list[Insight]:
    insights = []
    comparison = analysis.get("period_comparison")
    measure = "revenue" if analysis.get("revenue_source") else "record count"
    fmt = _money if analysis.get("revenue_source") else (lambda value: f"{value:,.0f}")
    if comparison and comparison["change_percent"] is not None:
        change = comparison["change_percent"]
        verb = "rose" if change > 0 else "fell" if change < 0 else "was unchanged"
        insights.append(
            Insight(
                id="period-comparison",
                category="trend",
                kind=FACT,
                title=f"{comparison['current']['label']} compared with {comparison['previous']['label']}",
                statement=(
                    f"{measure.capitalize()} {verb} by {_pct(abs(change))} from {comparison['previous']['label']} "
                    f"to {comparison['current']['label']}."
                    if change
                    else f"{measure.capitalize()} was unchanged from {comparison['previous']['label']} to {comparison['current']['label']}."
                ),
                evidence=[
                    Evidence(comparison["previous"]["label"], fmt(comparison["previous"]["value"])),
                    Evidence(comparison["current"]["label"], fmt(comparison["current"]["value"])),
                    Evidence("Change", f"{comparison['change']:+,.2f}"),
                ],
                caveat=comparison.get("note")
                or "A change between two periods may reflect seasonality or one-off events rather than a lasting trend.",
            )
        )
    trend = analysis.get("trend")
    if trend:
        if trend["direction"] == "flat":
            statement = f"Across {trend['periods']} complete periods ({trend['first_label']} to {trend['last_label']}), {measure} shows no clear upward or downward direction."
        else:
            statement = (
                f"Across {trend['periods']} complete periods ({trend['first_label']} to {trend['last_label']}), {measure} follows an "
                f"{trend['direction']} line of best fit, changing by about {_pct(abs(trend['relative_slope_percent']))} of the average per period."
            )
        insights.append(
            Insight(
                id="overall-trend",
                category="trend",
                kind=INTERPRETATION,
                title=f"Overall {trend['direction']} trend" if trend["direction"] != "flat" else "No clear overall trend",
                statement=statement,
                evidence=[
                    Evidence("Slope per period", f"{trend['slope_per_period']:+,.2f}"),
                    Evidence("Periods analysed", str(trend["periods"])),
                ],
                caveat="A straight-line fit summarises direction only. It is not a forecast and does not explain why values changed.",
            )
        )
    return insights


def _distribution_insights(analysis: dict) -> list[Insight]:
    mean = _metric(analysis, "average_transaction_value")
    median = _metric(analysis, "median_transaction_value")
    if not (mean and median and median["value"]):
        return []
    ratio = mean["value"] / median["value"]
    if ratio < 1.3:
        return []
    return [
        Insight(
            id="skewed-transactions",
            category="composition",
            kind=INTERPRETATION,
            title="A minority of large transactions raise the average",
            statement=f"The average transaction value ({_money(mean['value'])}) is {ratio:.1f}× the median ({_money(median['value'])}), which indicates that a smaller number of high-value transactions pull the average up.",
            evidence=[Evidence("Mean", _money(mean["value"])), Evidence("Median", _money(median["value"]))],
            caveat="The median is a better description of a typical transaction in skewed data.",
        )
    ]


def _status_insights(analysis: dict) -> list[Insight]:
    breakdown = analysis.get("breakdowns", {}).get("status")
    if not breakdown:
        return []
    negative = [row for row in breakdown["rows"] if any(word in row["group"].lower() for word in _NEGATIVE_STATUS_WORDS)]
    if not negative:
        return []
    total_records = sum(row["records"] for row in breakdown["rows"])
    negative_records = sum(row["records"] for row in negative)
    share = negative_records / total_records * 100 if total_records else 0
    names = ", ".join(f"'{row['group']}'" for row in negative)
    insights = [
        Insight(
            id="negative-status",
            category="performance",
            kind=FACT,
            title="Cancelled or returned records",
            statement=f"{negative_records:,} records ({_pct(share)}) have a status of {names}.",
            evidence=[Evidence(row["group"], f"{row['records']:,} records") for row in negative],
        )
    ]
    if breakdown["measure"] == "revenue":
        insights.append(
            Insight(
                id="status-in-totals",
                category="recommendation",
                kind=SUGGESTION,
                title="Check whether totals should include every status",
                statement=f"Revenue totals currently include records with status {names}. If these orders did not result in income, consider analysing completed orders separately.",
                evidence=[Evidence("Revenue in these statuses", _money(sum(row["revenue"] or 0 for row in negative)))],
            )
        )
    return insights


def _relationship_insights(analysis: dict) -> list[Insight]:
    insights = []
    for pair in analysis.get("correlations", [])[:2]:
        direction = "positive" if pair["coefficient"] > 0 else "negative"
        caveat = "Correlation does not show that one value causes the other."
        if pair["expected"]:
            caveat += " These columns are arithmetically related (revenue depends on quantity and price), so a relationship is expected."
        insights.append(
            Insight(
                id=f"correlation-{pair['column_a']}-{pair['column_b']}",
                category="relationship",
                kind=FACT,
                title=f"{pair['strength'].title()} {direction} relationship: {pair['column_a']} and {pair['column_b']}",
                statement=f"'{pair['column_a']}' and '{pair['column_b']}' have a Pearson correlation of {pair['coefficient']:+.2f}.",
                evidence=[Evidence("Correlation coefficient", f"{pair['coefficient']:+.3f}")],
                caveat=caveat,
            )
        )
    return insights


def _quality_insights(quality: dict) -> list[Insight]:
    serious = [finding for finding in quality.get("findings", []) if finding["severity"] in ("error", "warning")]
    if not serious:
        return []
    return [
        Insight(
            id="data-quality",
            category="data_quality",
            kind=FACT,
            title=f"{len(serious)} data quality issue{'s' if len(serious) != 1 else ''} may affect results",
            statement="The following issues can change totals or comparisons: "
            + "; ".join(finding["title"] for finding in serious[:4])
            + ".",
            evidence=[Evidence(finding["title"], f"{finding['affected_rows']:,} rows") for finding in serious[:4]],
            caveat=f"Quality score {quality['score']} ({quality['grade']}). Review the Data Quality page before relying on these results.",
        )
    ]


def _follow_up_suggestions(analysis: dict) -> list[Insight]:
    roles = analysis.get("roles", {})
    suggestions = []
    if roles.get("region") and roles.get("category"):
        suggestions.append("Compare category performance within each region to see whether leading categories differ by region.")
    if roles.get("date") and analysis.get("revenue_source"):
        suggestions.append("Look at revenue by month for the leading category to check whether its lead is consistent over time.")
    if roles.get("product"):
        suggestions.append("Review the lowest-revenue products to understand whether they are new, seasonal or underperforming.")
    if not suggestions:
        return []
    return [
        Insight(
            id="follow-up",
            category="question",
            kind=SUGGESTION,
            title="Questions worth investigating next",
            statement=" ".join(suggestions),
        )
    ]


def generate_rule_based_insights(analysis: dict, quality: dict) -> list[Insight]:
    insights: list[Insight] = []
    insights.extend(_trend_insights(analysis))
    insights.extend(_top_group_insights(analysis))
    insights.extend(_distribution_insights(analysis))
    insights.extend(_status_insights(analysis))
    insights.extend(_relationship_insights(analysis))
    insights.extend(_quality_insights(quality))
    insights.extend(_follow_up_suggestions(analysis))
    return insights
