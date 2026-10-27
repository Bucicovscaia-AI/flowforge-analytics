"""Inspection (profile_dataset) and cleaning rules C1-C8."""

import pandas as pd

from app.services.cleaning import clean_dataset, profile_dataset

COLUMNS = ["order_id", "order_date", "product_category", "region", "quantity", "unit_price"]


def frame(rows):
    return pd.DataFrame(rows, columns=COLUMNS, dtype=str)


def steps_by_rule(result):
    return {s["rule"]: s for s in result.steps}


def test_profile_counts_missing_values_per_column():
    df = frame([
        ["A1", "2026-01-01", "Books", "", "1", "5"],
        ["A2", "2026-01-02", "N/A", "North", "1", "5"],
        ["A3", "2026-01-03", "Books", "North", "1", "5"],
    ])
    profile = profile_dataset(df)
    by_name = {c["name"]: c for c in profile["column_profile"]}
    assert by_name["region"]["missing"] == 1
    assert by_name["product_category"]["missing"] == 1
    assert profile["missing_cells"] == 2
    assert profile["completeness_pct"] == round((1 - 2 / 18) * 100, 2)


def test_profile_counts_duplicates_and_invalid_values():
    df = frame([
        ["A1", "2026-01-01", "Books", "North", "1", "5"],
        ["A1", "2026-01-01", "Books", "North", "1", "5"],
        ["A2", "31/02/2026", "Books", "North", "-1", "abc"],
    ])
    profile = profile_dataset(df)
    by_name = {c["name"]: c for c in profile["column_profile"]}
    assert profile["duplicate_rows"] == 1
    assert by_name["order_date"]["invalid"] == 1
    assert by_name["quantity"]["invalid"] == 1
    assert by_name["unit_price"]["invalid"] == 1


def test_exact_duplicates_are_removed_keeping_first():
    df = frame([
        ["A1", "2026-01-01", "Books", "North", "1", "5"],
        ["A1 ", "2026-01-01", "Books", "North", "1", "5"],  # same after trimming
        ["A2", "2026-01-01", "Books", "North", "1", "5"],
    ])
    result = clean_dataset(df)
    assert len(result.frame) == 2
    assert steps_by_rule(result)["C2"]["rows_removed"] == 1


def test_rows_missing_required_values_are_removed():
    df = frame([
        ["A1", "2026-01-01", "Books", "North", "1", ""],
        ["", "2026-01-01", "Books", "North", "1", "5"],
        ["A3", "2026-01-01", "Books", "North", "null", "5"],
        ["A4", "2026-01-01", "Books", "North", "1", "5"],
    ])
    result = clean_dataset(df)
    assert result.frame["order_id"].tolist() == ["A4"]
    assert steps_by_rule(result)["C3"]["rows_removed"] == 3


def test_invalid_dates_quantities_and_prices_are_removed():
    df = frame([
        ["A1", "2026-02-30", "Books", "North", "1", "5"],  # impossible date
        ["A2", "15/03/2026", "Books", "North", "2", "5"],  # UK format is accepted
        ["A3", "2026-01-01", "Books", "North", "-2", "5"],
        ["A4", "2026-01-01", "Books", "North", "1.5", "5"],
        ["A5", "2026-01-01", "Books", "North", "1", "-3"],
        ["A6", "2026-01-01", "Books", "North", "1", "£1,250.00"],
    ])
    result = clean_dataset(df)
    rules = steps_by_rule(result)
    assert rules["C4"]["rows_removed"] == 1
    assert rules["C5"]["rows_removed"] == 2
    assert rules["C6"]["rows_removed"] == 1
    assert result.frame["order_id"].tolist() == ["A2", "A6"]
    assert result.frame.loc[1, "unit_price"] == 1250.0
    assert result.frame.loc[0, "order_date"] == pd.Timestamp("2026-03-15")


def test_category_spelling_made_consistent_and_missing_filled():
    df = frame([
        ["A1", "2026-01-01", "Books", "North", "1", "5"],
        ["A2", "2026-01-01", "Books", "North", "1", "5"],
        ["A3", "2026-01-01", "Books", "north", "1", "5"],
        ["A4", "2026-01-01", "", "NORTH", "1", "5"],
    ])
    result = clean_dataset(df)
    assert set(result.frame["region"]) == {"North"}
    assert result.frame.loc[3, "product_category"] == "Unknown"
    rules = steps_by_rule(result)
    assert rules["C7"]["cells_changed"] == 2
    assert rules["C8"]["cells_changed"] == 1


def test_revenue_column_and_row_counts():
    df = frame([["A1", "2026-01-01", "Books", "North", "3", "2.50"], ["A2", "bad", "Books", "North", "1", "1"]])
    result = clean_dataset(df)
    assert result.frame.loc[0, "revenue"] == 7.5
    assert result.rows_received == 2 and result.rows_removed == 1
    assert [s["rule"] for s in result.steps] == ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"]


def test_cleaning_does_not_modify_input():
    df = frame([["A1", " 2026-01-01 ", "Books", "North", "1", "5"]])
    clean_dataset(df)
    assert df.loc[0, "order_date"] == " 2026-01-01 "
