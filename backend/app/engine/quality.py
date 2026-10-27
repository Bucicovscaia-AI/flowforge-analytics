"""Data quality engine.

Each check is a plain function registered in `QUALITY_RULES`. A check receives
a `QualityContext` and returns zero or more `Finding` objects. New checks can
be added by writing a function and appending it to the registry.

Quality score
-------------
The score estimates the share of cells that are free of known problems:

    score = 100 x (1 - min(1, sum(weight x affected_cells) / total_cells))

where the weight is 1.0 for errors, 0.5 for warnings and 0 for informational
findings. It is a summary indicator, not a guarantee that the data is correct.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

import pandas as pd

from app.engine.profiling import (
    CATEGORICAL,
    DATETIME,
    EMPTY,
    IDENTIFIER,
    NUMERIC,
    TEXT,
    DatasetProfile,
    best_date_format,
    parse_dates,
    parse_numeric,
)

ERROR = "error"
WARNING = "warning"
INFO = "info"
SEVERITY_WEIGHT = {ERROR: 1.0, WARNING: 0.5, INFO: 0.0}
SEVERITY_ORDER = {ERROR: 0, WARNING: 1, INFO: 2}

# Text columns where this share of values parse as numbers/dates are reported as
# containing invalid values rather than being treated as free text.
LIKELY_TYPE_THRESHOLD = 0.8


@dataclass
class SuggestedOperation:
    operation: str
    params: dict = field(default_factory=dict)
    label: str = ""


@dataclass
class Finding:
    rule: str
    severity: str
    title: str
    description: str
    impact: str
    affected_rows: int
    affected_cells: int
    column: str | None = None
    examples: list[str] = field(default_factory=list)
    suggestion: SuggestedOperation | None = None
    affected_percent: float = 0.0

    @property
    def id(self) -> str:
        return f"{self.rule}:{self.column or '*'}"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["id"] = self.id
        return data


@dataclass
class QualityContext:
    frame: pd.DataFrame
    typed: pd.DataFrame
    profile: DatasetProfile
    roles: dict[str, str | None]

    @property
    def rows(self) -> int:
        return len(self.frame)


@dataclass
class QualityReport:
    score: float
    grade: str
    row_count: int
    column_count: int
    total_cells: int
    missing_cells: int
    duplicate_rows: int
    findings: list[Finding]

    def counts(self) -> dict[str, int]:
        result = {ERROR: 0, WARNING: 0, INFO: 0}
        for finding in self.findings:
            result[finding.severity] += 1
        return result

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "grade": self.grade,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "total_cells": self.total_cells,
            "missing_cells": self.missing_cells,
            "duplicate_rows": self.duplicate_rows,
            "counts": self.counts(),
            "findings": [finding.to_dict() for finding in self.findings],
            "method": "Score = 100 × (1 − weighted affected cells ÷ total cells). Errors weigh 1.0, warnings 0.5, information 0.",
        }


def _percent(part: int, whole: int) -> float:
    return round(part / whole * 100, 2) if whole else 0.0


def _examples(values: pd.Series, limit: int = 5) -> list[str]:
    return [str(value) for value in values.dropna().drop_duplicates().head(limit)]


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


def check_missing_values(context: QualityContext) -> list[Finding]:
    findings = []
    for column in context.profile.columns:
        if column.missing_count == 0:
            continue
        share = column.missing_count / context.rows
        if column.inferred_type == EMPTY:
            severity, title = ERROR, f"'{column.name}' is completely empty"
        elif share > 0.5:
            severity, title = ERROR, f"'{column.name}' is mostly empty"
        elif share >= 0.05:
            severity, title = WARNING, f"Missing values in '{column.name}'"
        else:
            severity, title = INFO, f"A few missing values in '{column.name}'"
        if column.inferred_type == EMPTY or share > 0.9:
            suggestion = SuggestedOperation("drop_column", {"column": column.name}, "Remove this column")
        elif column.inferred_type == NUMERIC:
            suggestion = SuggestedOperation("fill_missing", {"column": column.name, "strategy": "median"}, "Fill with median")
        else:
            suggestion = SuggestedOperation(
                "fill_missing", {"column": column.name, "strategy": "constant", "value": "Unknown"}, "Fill with 'Unknown'"
            )
        findings.append(
            Finding(
                rule="missing_values",
                severity=severity,
                column=column.name,
                title=title,
                description=f"{column.missing_count:,} of {context.rows:,} rows ({_percent(column.missing_count, context.rows)}%) have no value.",
                impact="Rows without a value are excluded from calculations that use this column, which can understate totals or skew comparisons.",
                affected_rows=column.missing_count,
                affected_cells=column.missing_count,
                suggestion=suggestion,
            )
        )
    return findings


def check_duplicate_rows(context: QualityContext) -> list[Finding]:
    duplicated = context.frame.duplicated(keep="first")
    count = int(duplicated.sum())
    if count == 0:
        return []
    return [
        Finding(
            rule="duplicate_rows",
            severity=WARNING,
            title="Duplicate rows",
            description=f"{count:,} rows are exact copies of an earlier row.",
            impact="Duplicates are counted more than once, inflating totals such as revenue and record counts.",
            affected_rows=count,
            affected_cells=count * context.frame.shape[1],
            examples=[f"Row {index + 2}" for index in duplicated[duplicated].index[:5]],
            suggestion=SuggestedOperation("remove_duplicates", {}, "Remove duplicate rows"),
        )
    ]


def check_duplicate_identifiers(context: QualityContext) -> list[Finding]:
    findings = []
    deduplicated = context.frame.drop_duplicates()
    for column in context.profile.columns:
        if column.inferred_type != IDENTIFIER:
            continue
        values = deduplicated[column.name].dropna()
        repeated = values[values.duplicated(keep=False)]
        if repeated.empty:
            continue
        findings.append(
            Finding(
                rule="duplicate_identifiers",
                severity=WARNING,
                column=column.name,
                title=f"Repeated identifiers in '{column.name}'",
                description=f"{repeated.nunique():,} identifier values appear on more than one distinct row.",
                impact="If each identifier should be unique, these rows may describe the same record with conflicting details.",
                affected_rows=len(repeated),
                affected_cells=len(repeated),
                examples=_examples(repeated),
            )
        )
    return findings


def check_invalid_numbers(context: QualityContext) -> list[Finding]:
    findings = []
    for column in context.profile.columns:
        raw = context.frame[column.name].dropna()
        if raw.empty:
            continue
        if column.inferred_type == NUMERIC and column.invalid_count:
            parsed = parse_numeric(raw)
        elif column.inferred_type in (TEXT, CATEGORICAL):
            parsed = parse_numeric(raw)
            rate = parsed.notna().mean()
            if rate < LIKELY_TYPE_THRESHOLD or rate == 1.0:
                continue
        else:
            continue
        invalid = raw[parsed.isna()]
        findings.append(
            Finding(
                rule="invalid_numbers",
                severity=ERROR,
                column=column.name,
                title=f"Non-numeric values in numeric column '{column.name}'",
                description=f"{len(invalid):,} values in a mostly numeric column cannot be read as numbers.",
                impact="These values are excluded from sums, averages and charts until they are corrected or converted.",
                affected_rows=len(invalid),
                affected_cells=len(invalid),
                examples=_examples(invalid),
                suggestion=SuggestedOperation("convert_numeric", {"column": column.name}, "Convert to numbers"),
            )
        )
    return findings


def check_invalid_dates(context: QualityContext) -> list[Finding]:
    findings = []
    for column in context.profile.columns:
        raw = context.frame[column.name].dropna()
        if raw.empty:
            continue
        if column.inferred_type == DATETIME and column.invalid_count:
            date_format = column.date_format
        elif column.inferred_type in (TEXT, CATEGORICAL):
            date_format, rate = best_date_format(raw)
            if not date_format or rate < LIKELY_TYPE_THRESHOLD or rate == 1.0:
                continue
        else:
            continue
        invalid = raw[parse_dates(raw, date_format).isna()]
        findings.append(
            Finding(
                rule="invalid_dates",
                severity=ERROR,
                column=column.name,
                title=f"Unreadable dates in '{column.name}'",
                description=f"{len(invalid):,} values do not match the column's date format ({date_format}).",
                impact="Rows with unreadable dates are left out of time-based analysis such as monthly trends.",
                affected_rows=len(invalid),
                affected_cells=len(invalid),
                examples=_examples(invalid),
                suggestion=SuggestedOperation("convert_datetime", {"column": column.name}, "Convert to dates"),
            )
        )
    return findings


def _normalised_text(values: pd.Series) -> pd.Series:
    return values.astype("string").str.strip().str.replace(r"\s+", " ", regex=True).str.casefold()


def check_inconsistent_categories(context: QualityContext) -> list[Finding]:
    findings = []
    for column in context.profile.columns:
        if column.inferred_type != CATEGORICAL:
            continue
        values = context.frame[column.name].dropna().astype("string")
        normalised = _normalised_text(values)
        variants = values.groupby(normalised).agg(lambda group: sorted(set(group)))
        inconsistent = variants[variants.map(len) > 1]
        if inconsistent.empty:
            continue
        most_common_form = values.groupby(normalised).agg(lambda group: group.mode().iloc[0])
        affected = int((values != normalised.map(most_common_form)).sum())
        examples = [" / ".join(f"'{variant}'" for variant in group[:3]) for group in inconsistent.head(3)]
        findings.append(
            Finding(
                rule="inconsistent_categories",
                severity=WARNING,
                column=column.name,
                title=f"Inconsistent spelling in '{column.name}'",
                description=f"{len(inconsistent)} categories appear with different capitalisation or spacing ({affected:,} values differ from the most common form).",
                impact="Variants are counted as separate categories, splitting totals across groups that should be combined.",
                affected_rows=affected,
                affected_cells=affected,
                examples=examples,
                suggestion=SuggestedOperation("normalise_text", {"column": column.name, "case": "title"}, "Normalise text"),
            )
        )
    return findings


def check_negative_values(context: QualityContext) -> list[Finding]:
    findings = []
    for role in ("revenue", "quantity", "unit_price"):
        column = context.roles.get(role)
        if not column or column not in context.typed:
            continue
        values = context.typed[column]
        negative = values[values < 0]
        if negative.empty:
            continue
        findings.append(
            Finding(
                rule="negative_values",
                severity=WARNING,
                column=column,
                title=f"Negative values in '{column}'",
                description=f"{len(negative):,} rows have a negative {role.replace('_', ' ')}.",
                impact="Negative values may represent refunds or returns, or may be entry errors. They reduce totals and averages.",
                affected_rows=len(negative),
                affected_cells=len(negative),
                examples=_examples(context.frame.loc[negative.index, column]),
            )
        )
    return findings


def check_outliers(context: QualityContext) -> list[Finding]:
    findings = []
    for column in context.profile.columns:
        if column.inferred_type != NUMERIC:
            continue
        values = context.typed[column.name].dropna()
        if len(values) < 20 or values.nunique() < 5:
            continue
        q1, q3 = values.quantile(0.25), values.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 3 * iqr, q3 + 3 * iqr
        outliers = values[(values < lower) | (values > upper)]
        if outliers.empty:
            continue
        findings.append(
            Finding(
                rule="outliers",
                severity=INFO,
                column=column.name,
                title=f"Extreme values in '{column.name}'",
                description=(
                    f"{len(outliers):,} values fall outside the range {lower:,.2f} to {upper:,.2f} "
                    "(more than three interquartile ranges beyond the middle 50% of values)."
                ),
                impact="Extreme values can be genuine (for example, a large order) but can also be errors. They have a strong effect on averages.",
                affected_rows=len(outliers),
                affected_cells=len(outliers),
                examples=[f"{value:,.2f}" for value in outliers.sort_values(ascending=False).head(5)],
            )
        )
    return findings


def check_constant_columns(context: QualityContext) -> list[Finding]:
    findings = []
    if context.rows < 2:
        return findings
    for column in context.profile.columns:
        if column.inferred_type == EMPTY or column.distinct_count != 1:
            continue
        findings.append(
            Finding(
                rule="constant_column",
                severity=INFO,
                column=column.name,
                title=f"'{column.name}' has a single value",
                description=f"Every non-empty row contains '{column.sample_values[0]}'.",
                impact="A column with one value cannot explain differences between records and is usually safe to ignore.",
                affected_rows=0,
                affected_cells=0,
                suggestion=SuggestedOperation("drop_column", {"column": column.name}, "Remove this column"),
            )
        )
    return findings


def check_revenue_consistency(context: QualityContext) -> list[Finding]:
    revenue, quantity, price = (context.roles.get(role) for role in ("revenue", "quantity", "unit_price"))
    if not (revenue and quantity and price):
        return []
    typed = context.typed[[revenue, quantity, price]].dropna()
    if typed.empty:
        return []
    expected = typed[quantity] * typed[price]
    tolerance = (typed[revenue].abs() * 0.005).clip(lower=0.01)
    mismatched = typed[(typed[revenue] - expected).abs() > tolerance]
    if mismatched.empty:
        return []
    return [
        Finding(
            rule="revenue_mismatch",
            severity=WARNING,
            column=revenue,
            title=f"'{revenue}' does not equal {quantity} × {price}",
            description=f"{len(mismatched):,} rows have a {revenue} value that differs from quantity multiplied by unit price by more than 0.5%.",
            impact="Discounts, taxes or shipping may explain the difference; otherwise one of the three values is likely wrong.",
            affected_rows=len(mismatched),
            affected_cells=len(mismatched),
            examples=[f"Row {index + 2}" for index in mismatched.index[:5]],
        )
    ]


def check_future_dates(context: QualityContext) -> list[Finding]:
    findings = []
    limit = pd.Timestamp(datetime.now() + timedelta(days=1))
    for column in context.profile.columns:
        if column.inferred_type != DATETIME:
            continue
        values = context.typed[column.name].dropna()
        future = values[values > limit]
        if future.empty:
            continue
        findings.append(
            Finding(
                rule="future_dates",
                severity=INFO,
                column=column.name,
                title=f"Future dates in '{column.name}'",
                description=f"{len(future):,} dates are later than today.",
                impact="Future dates may be planned events or entry errors; they extend time-based charts beyond the present.",
                affected_rows=len(future),
                affected_cells=len(future),
                examples=[value.strftime("%Y-%m-%d") for value in future.head(5)],
            )
        )
    return findings


QualityRule = Callable[[QualityContext], list[Finding]]

QUALITY_RULES: list[QualityRule] = [
    check_missing_values,
    check_duplicate_rows,
    check_duplicate_identifiers,
    check_invalid_numbers,
    check_invalid_dates,
    check_inconsistent_categories,
    check_negative_values,
    check_revenue_consistency,
    check_outliers,
    check_future_dates,
    check_constant_columns,
]


def grade_for(score: float) -> str:
    if score >= 95:
        return "Excellent"
    if score >= 85:
        return "Good"
    if score >= 70:
        return "Fair"
    return "Poor"


def assess_quality(context: QualityContext, rules: list[QualityRule] | None = None) -> QualityReport:
    findings: list[Finding] = []
    for rule in rules or QUALITY_RULES:
        findings.extend(rule(context))
    for finding in findings:
        finding.affected_percent = _percent(finding.affected_rows, context.rows)
    findings.sort(key=lambda finding: (SEVERITY_ORDER[finding.severity], -finding.affected_rows))

    total_cells = context.frame.size
    weighted = sum(SEVERITY_WEIGHT[finding.severity] * finding.affected_cells for finding in findings)
    score = round(100 * (1 - min(1.0, weighted / total_cells)), 1) if total_cells else 0.0
    return QualityReport(
        score=score,
        grade=grade_for(score),
        row_count=context.rows,
        column_count=context.frame.shape[1],
        total_cells=int(total_cells),
        missing_cells=int(context.frame.isna().sum().sum()),
        duplicate_rows=int(context.frame.duplicated().sum()),
        findings=findings,
    )
