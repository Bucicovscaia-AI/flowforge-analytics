"""Server-side file validation (csv_loader.load_csv)."""

import pytest

from app.services.csv_loader import DatasetError, load_csv, normalise_header
from tests.conftest import VALID_CSV

LIMITS = {"max_bytes": 1024 * 1024, "max_rows": 1000, "max_columns": 20}


def load(content, name="orders.csv", content_type="text/csv", **overrides):
    raw = content.encode() if isinstance(content, str) else content
    return load_csv(raw, name, content_type, **{**LIMITS, **overrides})


def test_valid_csv_is_loaded_as_text():
    loaded = load(VALID_CSV)
    assert len(loaded.frame) == 5
    assert loaded.frame["quantity"].tolist()[0] == "2"  # not converted yet
    assert loaded.encoding == "UTF-8"


def test_headers_are_normalised_and_aliases_applied():
    loaded = load("Order ID,Date,Qty,Price,Category\nA1,2026-01-01,1,2.50,Books\n")
    assert list(loaded.frame.columns) == ["order_id", "order_date", "quantity", "unit_price", "product_category"]
    assert loaded.renamed_columns["Qty"] == "quantity"


@pytest.mark.parametrize("raw, expected", [("Order Date ", "order_date"), ("unit-price", "unit_price"), ("Customer Segment", "customer_type")])
def test_normalise_header(raw, expected):
    assert normalise_header(raw) == expected


def test_semicolon_delimited_file_is_accepted():
    loaded = load("order_id;order_date;quantity;unit_price\nA1;2026-01-01;1;2.50\n")
    assert len(loaded.frame) == 1


def test_utf8_bom_and_windows_1252_are_decoded():
    assert load(b"\xef\xbb\xbf" + VALID_CSV.encode()).frame.shape[0] == 5
    cp = "order_id,order_date,quantity,unit_price,product\nA1,2026-01-01,1,2.50,Caf\xe9 mug\n".encode("cp1252")
    loaded = load(cp)
    assert loaded.encoding == "Windows-1252"
    assert loaded.frame["product"][0] == "Café mug"


@pytest.mark.parametrize("name", ["orders.xlsx", "orders.pdf", "orders", "orders.csv.exe"])
def test_rejects_non_csv_extension(name):
    with pytest.raises(DatasetError) as err:
        load(VALID_CSV, name=name)
    assert err.value.status_code == 415


def test_rejects_disallowed_content_type():
    with pytest.raises(DatasetError) as err:
        load(VALID_CSV, content_type="application/pdf")
    assert err.value.status_code == 415


def test_rejects_binary_content_with_csv_name():
    with pytest.raises(DatasetError, match="binary"):
        load(b"PK\x03\x04\x00\x00binarydata", name="sheet.csv")


def test_rejects_empty_file():
    with pytest.raises(DatasetError, match="empty") as err:
        load(b"")
    assert err.value.status_code == 400


def test_rejects_whitespace_only_file():
    with pytest.raises(DatasetError, match="no data"):
        load("  \n\n ")


def test_rejects_header_without_rows():
    with pytest.raises(DatasetError, match="no data rows"):
        load("order_id,order_date,quantity,unit_price\n")


def test_rejects_file_over_size_limit():
    with pytest.raises(DatasetError) as err:
        load(VALID_CSV, max_bytes=50)
    assert err.value.status_code == 413


def test_rejects_too_many_rows():
    with pytest.raises(DatasetError, match="more than"):
        load(VALID_CSV, max_rows=3)


def test_rejects_too_many_columns():
    header = ",".join(f"c{i}" for i in range(25))
    with pytest.raises(DatasetError, match="columns"):
        load(header + "\n" + ",".join("1" * 25) + "\n")


@pytest.mark.parametrize(
    "body",
    [
        "A1,2026-01-01,1,2.5,extra,fields\n",
        "A1,2026-01-01,1,2.5\nA2,2026-01-02,1,2.5,extra\n",
        'A1,"2026-01-01,1,2.5\n',  # unclosed quote
    ],
)
def test_rejects_malformed_rows(body):
    with pytest.raises(DatasetError, match="malformed"):
        load("order_id,order_date,quantity,unit_price\n" + body)


def test_reports_all_missing_required_columns():
    with pytest.raises(DatasetError) as err:
        load("order_id,product\nA1,Lamp\n")
    assert err.value.status_code == 422
    assert "order_date" in err.value.message and "quantity" in err.value.message and "unit_price" in err.value.message


def test_rejects_duplicate_column_names():
    with pytest.raises(DatasetError, match="more than once"):
        load("order_id,order_date,quantity,unit_price,Qty\nA1,2026-01-01,1,2,3\n")


def test_file_name_is_sanitised():
    loaded = load(VALID_CSV, name="../../etc/<evil>.csv")
    assert loaded.file_name == "_evil_.csv"
