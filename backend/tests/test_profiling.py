import pandas as pd
import pytest

from app.engine.loading import CSVValidationError, parse_csv_bytes
from app.engine.profiling import (
    BOOLEAN,
    CATEGORICAL,
    DATETIME,
    IDENTIFIER,
    NUMERIC,
    TEXT,
    detect_roles,
    infer_column,
    parse_numeric,
    profile_frame,
    resolve_roles,
)


def column(values, name="value"):
    return pd.Series(values, name=name, dtype="str")


def test_parse_numeric_handles_currency_and_thousands():
    parsed = parse_numeric(pd.Series(["£1,234.50", "$20", " 7 ", "1,2", "abc", None]))
    assert parsed.tolist()[:3] == [1234.5, 20.0, 7.0]
    assert parsed.isna().tolist()[3:] == [True, True, True]


@pytest.mark.parametrize(
    "values, expected",
    [
        (["1", "2.5", "-3"], NUMERIC),
        (["2025-01-01", "2025-02-01", "2025-03-01"], DATETIME),
        (["03/04/2025", "15/04/2025", "28/02/2025"], DATETIME),
        (["yes", "no", "yes"], BOOLEAN),
        (["North", "South", "North"], CATEGORICAL),
        (["00123", "00456", "00789"], CATEGORICAL),
    ],
)
def test_type_inference(values, expected):
    assert infer_column(column(values)).inferred_type == expected


def test_day_first_dates_are_reported():
    profile = infer_column(column(["03/04/2025", "15/04/2025"]))
    assert profile.date_format == "%d/%m/%Y"


def test_mostly_numeric_column_counts_invalid_values():
    values = [str(number) for number in range(19)] + ["n/a-ish"]
    profile = infer_column(column(values, "amount"))
    assert profile.inferred_type == NUMERIC
    assert profile.invalid_count == 1


def test_identifier_detection():
    assert infer_column(column([str(n) for n in range(1, 30)], "customer_id")).inferred_type == IDENTIFIER
    long_text = [f"Free text comment number {n} with words" for n in range(60)]
    assert infer_column(column(long_text, "comment")).inferred_type == TEXT


def test_missing_markers_and_whitespace_are_missing():
    parsed = parse_csv_bytes(b"a,b\n1,N/A\n2,   \n3,x\n", max_rows=100, max_columns=10)
    assert parsed.frame["b"].isna().tolist() == [True, True, False]


def test_parse_rejects_too_many_rows():
    with pytest.raises(CSVValidationError) as error:
        parse_csv_bytes(b"a\n1\n2\n3\n", max_rows=2, max_columns=10)
    assert error.value.code == "too_many_rows"


def test_parse_rejects_rows_with_extra_fields():
    with pytest.raises(CSVValidationError) as error:
        parse_csv_bytes(b"a,b\n1,2\n3,4,5\n", max_rows=10, max_columns=10)
    assert error.value.code == "malformed_csv"


def test_role_detection_and_overrides():
    frame = pd.DataFrame(
        {
            "Order Date": ["2025-01-01", "2025-01-02"],
            "Qty": ["1", "2"],
            "Price": ["5", "6"],
            "Sales Amount": ["5", "12"],
            "Product Category": ["A", "B"],
            "Country": ["UK", "FR"],
        },
        dtype="str",
    )
    profile = profile_frame(frame)
    roles = detect_roles(profile)
    assert roles == {
        "date": "Order Date",
        "quantity": "Qty",
        "unit_price": "Price",
        "revenue": "Sales Amount",
        "category": "Product Category",
        "product": None,
        "region": "Country",
        "status": None,
    }
    overridden = resolve_roles(profile, {"region": "", "revenue": "Product Category", "product": "Country"})
    assert overridden["region"] is None
    assert overridden["revenue"] == "Sales Amount"  # incompatible override ignored
    assert overridden["product"] == "Country"
