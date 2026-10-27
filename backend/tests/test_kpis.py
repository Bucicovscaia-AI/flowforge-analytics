"""KPI calculations, including the required-column checks."""

import pandas as pd
import pytest

from app.services.cleaning import clean_dataset
from app.services.kpis import calculate_kpis


@pytest.fixture
def cleaned():
    df = pd.DataFrame(
        [
            ["A1", "2026-01-05", "Lamp", "Home", "North", "2", "10"],
            ["A1", "2026-01-05", "Mug", "Home", "North", "1", "5"],
            ["A2", "2026-01-20", "Jacket", "Clothing", "South", "1", "50"],
            ["A3", "2026-02-03", "Lamp", "Home", "North", "3", "10"],
            ["A4", "2026-02-14", "Jacket", "Clothing", "South", "2", "50"],
        ],
        columns=["order_id", "order_date", "product", "product_category", "region", "quantity", "unit_price"],
        dtype=str,
    )
    return clean_dataset(df).frame


def test_headline_kpis(cleaned):
    s = calculate_kpis(cleaned)["summary"]
    # 20 + 5 + 50 + 30 + 100
    assert s["total_revenue"] == 205.0
    assert s["order_count"] == 4  # A1 has two lines but is one order
    assert s["units_sold"] == 9
    assert s["average_order_value"] == 51.25
    assert s["order_lines"] == 5
    assert (s["date_from"], s["date_to"]) == ("2026-01-05", "2026-02-14")


def test_revenue_by_category_and_region(cleaned):
    b = calculate_kpis(cleaned)["breakdowns"]
    assert [(r["name"], r["revenue"]) for r in b["revenue_by_category"]] == [("Clothing", 150.0), ("Home", 55.0)]
    north = next(r for r in b["revenue_by_region"] if r["name"] == "North")
    assert north["orders"] == 2 and north["average_order_value"] == 27.5
    assert round(sum(r["share_pct"] for r in b["revenue_by_region"]), 1) == 100.0


def test_revenue_over_time_is_monthly(cleaned):
    months = calculate_kpis(cleaned)["breakdowns"]["revenue_over_time"]
    assert [(m["period"], m["revenue"], m["orders"]) for m in months] == [("2026-01", 75.0, 2), ("2026-02", 130.0, 2)]
    assert months[0]["label"] == "Jan 2026"


def test_top_products(cleaned):
    top = calculate_kpis(cleaned)["breakdowns"]["top_products"]
    assert top[0]["name"] == "Jacket" and top[0]["units"] == 3


def test_kpis_needing_missing_columns_are_reported_unavailable(cleaned):
    result = calculate_kpis(cleaned.drop(columns=["region", "product_category"]))
    missing = {u["kpi"]: u["missing_columns"] for u in result["unavailable"]}
    assert missing["revenue_by_region"] == ["region"]
    assert missing["revenue_by_category"] == ["product_category"]
    assert "revenue_by_region" not in result["breakdowns"]
    assert result["summary"]["total_revenue"] == 205.0  # core KPIs still work


def test_missing_order_id_disables_order_kpis(cleaned):
    result = calculate_kpis(cleaned.drop(columns=["order_id"]))
    assert result["summary"]["order_count"] is None
    assert result["summary"]["average_order_value"] is None
    assert {"order_count", "average_order_value"} <= {u["kpi"] for u in result["unavailable"]}


def test_empty_cleaned_dataset_gives_zero_totals(cleaned):
    result = calculate_kpis(cleaned.iloc[0:0])
    assert result["summary"]["total_revenue"] == 0.0
    assert result["summary"]["order_count"] == 0
    assert result["summary"]["average_order_value"] is None
    assert result["breakdowns"] == {}
