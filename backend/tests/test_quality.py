import pandas as pd

from app.engine.profiling import profile_frame, resolve_roles, typed_frame
from app.engine.quality import QualityContext, assess_quality


def assess(frame: pd.DataFrame):
    frame = frame.astype("str").where(frame.notna(), None)
    profile = profile_frame(frame)
    roles = resolve_roles(profile, {})
    return assess_quality(QualityContext(frame, typed_frame(frame, profile), profile, roles))


def finding(report, rule, column=None):
    return next(item for item in report.findings if item.rule == rule and (column is None or item.column == column))


def test_clean_data_scores_100():
    frame = pd.DataFrame({"region": ["North", "South", "East", "West"], "revenue": ["1", "2", "3", "4"]})
    report = assess(frame)
    assert report.score == 100.0
    assert report.findings == []
    assert report.grade == "Excellent"


def test_missing_values_are_counted_per_column():
    frame = pd.DataFrame({"a": ["1", None, "3", None], "b": ["x", "y", "z", "w"]})
    report = assess(frame)
    result = finding(report, "missing_values", "a")
    assert result.affected_rows == 2
    assert result.affected_percent == 50.0
    assert result.severity == "warning"
    assert report.missing_cells == 2


def test_duplicate_rows_detected_and_score_reflects_weight():
    frame = pd.DataFrame({"a": ["1", "1", "2", "3"], "b": ["x", "x", "y", "z"]})
    report = assess(frame)
    duplicate = finding(report, "duplicate_rows")
    assert duplicate.affected_rows == 1
    assert duplicate.affected_cells == 2
    # Warning weight 0.5 x 2 affected cells / 8 cells = 12.5% penalty.
    assert report.score == 87.5


def test_invalid_numbers_in_mostly_numeric_column():
    values = [str(number) for number in range(1, 10)] + ["twelve"]
    report = assess(pd.DataFrame({"amount": values}))
    result = finding(report, "invalid_numbers", "amount")
    assert result.affected_rows == 1
    assert result.examples == ["twelve"]
    assert result.suggestion.operation == "convert_numeric"


def test_invalid_dates_detected():
    values = [f"2025-01-{day:02d}" for day in range(1, 11)] + ["2025-13-45"]
    report = assess(pd.DataFrame({"order_date": values}))
    result = finding(report, "invalid_dates", "order_date")
    assert result.affected_rows == 1
    assert result.examples == ["2025-13-45"]


def test_inconsistent_categories_detected():
    frame = pd.DataFrame({"region": ["North", "North", "north", " North ", "South", "South"]})
    result = finding(assess(frame), "inconsistent_categories", "region")
    assert result.affected_rows == 2
    assert result.suggestion.operation == "normalise_text"


def test_negative_values_and_revenue_mismatch():
    frame = pd.DataFrame(
        {
            "quantity": ["1", "2", "3", "-1"],
            "unit_price": ["10", "10", "10", "10"],
            "revenue": ["10", "20", "35", "-10"],
        }
    )
    report = assess(frame)
    assert finding(report, "negative_values", "quantity").affected_rows == 1
    assert finding(report, "revenue_mismatch").affected_rows == 1


def test_constant_and_empty_columns():
    frame = pd.DataFrame({"a": ["x", "x", "x"], "b": [None, None, None], "c": ["1", "2", "3"]})
    report = assess(frame)
    assert finding(report, "constant_column", "a").severity == "info"
    empty = finding(report, "missing_values", "b")
    assert empty.severity == "error"
    assert empty.suggestion.operation == "drop_column"


def test_outliers_flagged_as_information():
    values = [str(value) for value in [10, 11, 12, 13, 14, 10, 11, 12, 13, 14] * 2] + ["500"]
    report = assess(pd.DataFrame({"amount": values}))
    result = finding(report, "outliers", "amount")
    assert result.severity == "info"
    assert result.affected_rows == 1
