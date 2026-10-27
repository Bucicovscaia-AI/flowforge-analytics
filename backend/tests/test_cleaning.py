import pandas as pd
import pytest

from app.engine.cleaning import OPERATIONS, CleaningError, apply_operation
from tests.conftest import upload


def frame(**columns):
    return pd.DataFrame(columns, dtype="str")


def test_remove_duplicates():
    data = frame(a=["1", "1", "2"], b=["x", "x", "x"])
    result, outcome = apply_operation(data, "remove_duplicates")
    assert len(result) == 2
    assert outcome.rows_before == 3 and outcome.rows_after == 2
    assert len(data) == 3  # input unchanged


@pytest.mark.parametrize("strategy, expected", [("mean", "2"), ("median", "1"), ("mode", "1")])
def test_fill_missing_statistics(strategy, expected):
    data = frame(n=["1", "1", None, "4"])
    data.loc[2, "n"] = None
    result, outcome = apply_operation(data, "fill_missing", {"column": "n", "strategy": strategy})
    assert result["n"].tolist()[2] == expected
    assert outcome.cells_changed == 1


def test_fill_missing_constant_and_validation():
    data = frame(region=["North", None])
    result, _ = apply_operation(data, "fill_missing", {"column": "region", "strategy": "constant", "value": "Unknown"})
    assert result["region"].tolist() == ["North", "Unknown"]
    with pytest.raises(CleaningError):
        apply_operation(data, "fill_missing", {"column": "region", "strategy": "mean"})
    with pytest.raises(CleaningError):
        apply_operation(frame(n=["1", None]), "fill_missing", {"column": "n", "strategy": "constant", "value": "abc"})


def test_drop_missing_rows():
    result, outcome = apply_operation(frame(a=["1", None, "3"]), "drop_missing_rows", {"column": "a"})
    assert result["a"].tolist() == ["1", "3"]
    assert outcome.to_dict()["rows_removed"] == 1


def test_convert_numeric_reports_invalid_values():
    result, outcome = apply_operation(frame(v=["£1,200.50", "7", "oops"]), "convert_numeric", {"column": "v"})
    assert result["v"].tolist()[:2] == ["1200.5", "7"]
    assert pd.isna(result["v"].tolist()[2])
    assert outcome.warnings == ["1 values could not be read as numbers and are now empty."]


def test_convert_datetime_to_iso():
    data = frame(d=["03/04/2025", "15/04/2025", "bad"])
    result, outcome = apply_operation(data, "convert_datetime", {"column": "d"})
    assert result["d"].tolist()[:2] == ["2025-04-03", "2025-04-15"]
    assert pd.isna(result["d"].tolist()[2])
    assert outcome.cells_changed == 3


def test_normalise_text():
    result, outcome = apply_operation(
        frame(r=[" north ", "SOUTH", "East  Side"]), "normalise_text", {"column": "r", "case": "title"}
    )
    assert result["r"].tolist() == ["North", "South", "East Side"]
    assert outcome.cells_changed == 3


def test_remove_invalid_rows_keeps_empty_cells():
    data = frame(n=["1", "x", None, "2"])
    result, _ = apply_operation(data, "remove_invalid_rows", {"column": "n", "kind": "number"})
    assert len(result) == 3


def test_drop_column_and_errors():
    result, _ = apply_operation(frame(a=["1"], b=["2"]), "drop_column", {"column": "b"})
    assert list(result.columns) == ["a"]
    with pytest.raises(CleaningError):
        apply_operation(frame(a=["1"]), "drop_column", {"column": "a"})
    with pytest.raises(CleaningError):
        apply_operation(frame(a=["1"]), "drop_column", {"column": "missing"})
    with pytest.raises(CleaningError):
        apply_operation(frame(a=["1"]), "not_an_operation")


def test_every_operation_is_described():
    for operation in OPERATIONS.values():
        description = operation.describe()
        assert description["description"] and description["consequence"]


def test_cleaning_api_preview_apply_and_reset(client):
    dataset_id = upload(client, "id,region\n1,North\n1,North\n2,south\n", "c.csv").json()["id"]

    preview = client.post(f"/api/datasets/{dataset_id}/cleaning/preview", json={"operation": "remove_duplicates"}).json()
    assert preview["applied"] is False and preview["rows_removed"] == 1
    assert client.get(f"/api/datasets/{dataset_id}").json()["row_count"] == 3

    applied = client.post(f"/api/datasets/{dataset_id}/cleaning/apply", json={"operation": "remove_duplicates"}).json()
    assert applied["applied"] is True and applied["rows_after"] == 2
    detail = client.get(f"/api/datasets/{dataset_id}").json()
    assert detail["row_count"] == 2 and detail["original_row_count"] == 3
    assert [operation["operation"] for operation in detail["operations"]] == ["remove_duplicates"]

    again = client.post(f"/api/datasets/{dataset_id}/cleaning/apply", json={"operation": "remove_duplicates"}).json()
    assert again["applied"] is False and "No changes" in again["message"]

    reset = client.post(f"/api/datasets/{dataset_id}/cleaning/reset").json()
    assert reset["row_count"] == 3


def test_cleaning_api_rejects_bad_operation(client):
    dataset_id = upload(client, "a\n1\n", "c.csv").json()["id"]
    response = client.post(
        f"/api/datasets/{dataset_id}/cleaning/apply", json={"operation": "drop_column", "params": {"column": "zz"}}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_operation"
    response = client.post(f"/api/datasets/{dataset_id}/cleaning/apply", json={"operation": "rm -rf"})
    assert response.status_code == 422


def test_operations_catalogue(client):
    keys = [item["key"] for item in client.get("/api/cleaning/operations").json()]
    assert "remove_duplicates" in keys and "convert_datetime" in keys
