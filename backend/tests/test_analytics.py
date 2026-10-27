import pandas as pd
import pytest

from app.engine import analytics
from app.engine.profiling import profile_frame, resolve_roles, typed_frame
from tests.conftest import KNOWN_CSV, upload


def context_from_csv(text: str, overrides=None) -> analytics.AnalysisContext:
    rows = [line.split(",") for line in text.strip().splitlines()]
    frame = pd.DataFrame(rows[1:], columns=rows[0], dtype="str")
    profile = profile_frame(frame)
    return analytics.AnalysisContext(typed_frame(frame, profile), profile, resolve_roles(profile, overrides))


def metric(result, key):
    return next(item for item in result["metrics"] if item["key"] == key)


def test_business_metrics_match_known_values():
    result = analytics.analyse(context_from_csv(KNOWN_CSV))
    assert metric(result, "records")["value"] == 6
    assert metric(result, "total_revenue")["value"] == 230.0
    assert metric(result, "average_transaction_value")["value"] == pytest.approx(38.33, abs=0.01)
    assert metric(result, "median_transaction_value")["value"] == 35.0
    assert metric(result, "total_quantity")["value"] == 13.0
    assert metric(result, "categories")["value"] == 2
    date_range = metric(result, "date_range")
    assert (date_range["start"], date_range["end"]) == ("2025-01-05", "2025-03-31")


def test_breakdowns_and_shares():
    result = analytics.analyse(context_from_csv(KNOWN_CSV))
    category = {row["group"]: row for row in result["breakdowns"]["category"]["rows"]}
    assert category["B"]["revenue"] == 130.0
    assert category["A"]["revenue"] == 100.0
    assert category["B"]["share"] == pytest.approx(56.52, abs=0.01)
    assert category["A"]["records"] == 3
    assert category["B"]["quantity"] == 7.0
    region = [row["group"] for row in result["breakdowns"]["region"]["rows"]]
    assert region == ["South", "North"]


def test_monthly_time_series_and_period_comparison():
    context = context_from_csv(KNOWN_CSV)
    revenue, _ = analytics.revenue_series(context)
    series = analytics.time_series(context.typed["order_date"], revenue, "sum", "month")
    assert [point["value"] for point in series["points"]] == [50.0, 80.0, 100.0]
    assert [point["partial"] for point in series["points"]] == [True, False, False]
    comparison = analytics.period_comparison(series)
    assert comparison["current"]["label"] == "Mar 2025"
    assert comparison["previous"]["label"] == "Feb 2025"
    assert comparison["change"] == 20.0
    assert comparison["change_percent"] == 25.0


def test_incomplete_latest_period_is_excluded_from_comparison():
    text = KNOWN_CSV + "7,2025-04-02,A,North,1,10,10\n"
    context = context_from_csv(text)
    revenue, _ = analytics.revenue_series(context)
    comparison = analytics.period_comparison(analytics.time_series(context.typed["order_date"], revenue, "sum", "month"))
    assert comparison["current"]["label"] == "Mar 2025"
    assert "incomplete" in comparison["note"]


def test_time_series_fills_empty_periods_with_zero():
    dates = pd.Series(pd.to_datetime(["2025-01-10", "2025-03-10"]))
    series = analytics.time_series(dates, pd.Series([5.0, 7.0]), "sum", "month")
    assert [point["value"] for point in series["points"]] == [5.0, 0.0, 7.0]


def test_aggregate_supports_mean_and_count():
    context = context_from_csv(KNOWN_CSV)
    mean = analytics.aggregate(context.typed, "region", context.typed["revenue"], "mean")
    assert {row["group"]: row["value"] for row in mean["rows"]} == {"South": pytest.approx(46.6667, abs=0.001), "North": 30.0}
    count = analytics.aggregate(context.typed, "category")
    assert {row["group"]: row["value"] for row in count["rows"]} == {"A": 3.0, "B": 3.0}
    assert count["aggregation"] == "count"


def test_distribution_counts():
    result = analytics.distribution(pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]), bins=2)
    assert [bin_["count"] for bin_ in result["bins"]] == [5, 5]
    assert result["median"] == 5.5


def test_revenue_is_derived_when_column_missing():
    text = "\n".join(",".join(line.split(",")[:6]) for line in KNOWN_CSV.strip().splitlines())
    result = analytics.analyse(context_from_csv(text))
    assert result["revenue_source"] == "derived"
    assert metric(result, "total_revenue")["value"] == 230.0
    assert any("calculated as quantity × unit_price" in note for note in result["limitations"])


def test_general_dataset_without_business_columns():
    text = "height,weight,species\n" + "\n".join(f"{150 + n},{50 + n * 2},{'cat' if n % 2 else 'dog'}" for n in range(12))
    result = analytics.analyse(context_from_csv(text))
    keys = {item["key"] for item in result["metrics"]}
    assert keys == {"records", "columns"}
    assert result["time_series"] is None
    assert any("No revenue column" in note for note in result["limitations"])
    assert any("No date column" in note for note in result["limitations"])
    assert result["correlations"][0]["coefficient"] == 1.0
    assert result["correlations"][0]["expected"] is False


def test_analysis_api_and_unsupported_requests(client, known_dataset):
    analysis = client.get(f"/api/datasets/{known_dataset}/analysis").json()
    assert metric(analysis, "total_revenue")["value"] == 230.0

    response = client.get(f"/api/datasets/{known_dataset}/charts/distribution", params={"column": "category"})
    assert response.status_code == 422
    assert "not a numeric column" in response.json()["error"]["message"]

    response = client.get(f"/api/datasets/{known_dataset}/charts/aggregate", params={"group_by": "nope"})
    assert response.status_code == 422


def test_timeseries_api_without_date_column(client):
    dataset_id = upload(client, "a,b\nx,1\ny,2\n", "nodate.csv").json()["id"]
    response = client.get(f"/api/datasets/{dataset_id}/charts/timeseries")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "no_date_column"


def test_aggregate_csv_export(client, known_dataset):
    response = client.get(
        f"/api/datasets/{known_dataset}/charts/aggregate.csv", params={"group_by": "region", "value": "revenue"}
    )
    assert response.status_code == 200
    lines = response.text.strip().splitlines()
    assert lines[0] == "region,sum_revenue,records,share_percent"
    assert lines[1].startswith("South,140.0,3")
