from tests.conftest import KNOWN_CSV, upload


def test_upload_valid_csv(client):
    response = upload(client, KNOWN_CSV, "Q1 sales.csv")
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Q1 sales"
    assert body["row_count"] == 6
    assert body["column_count"] == 7
    assert body["status"] == "ready"
    assert body["is_sample"] is False
    assert 0 <= body["quality_score"] <= 100


def test_upload_rejects_unsupported_extension(client):
    response = upload(client, "a,b\n1,2\n", "data.xlsx")
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_file_type"


def test_upload_rejects_unexpected_content_type(client):
    response = upload(client, "a,b\n1,2\n", "data.csv", content_type="application/x-msdownload")
    assert response.status_code == 415


def test_upload_rejects_empty_file(client):
    response = upload(client, "", "empty.csv")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "empty_file"


def test_upload_rejects_header_only_file(client):
    response = upload(client, "a,b,c\n", "header.csv")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "no_rows"


def test_upload_rejects_malformed_csv(client):
    response = upload(client, 'a,b\n1,2\n3,4,5,6\n"unterminated,7\n', "bad.csv")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "malformed_csv"


def test_upload_rejects_binary_content(client):
    response = upload(client, b"\x89PNG\r\n\x1a\n\x00\x00\x00", "image.csv")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "binary_content"


def test_upload_rejects_file_over_size_limit(client):
    row = "1,2,3,4,5,6,7,8,9,10\n"
    content = "a,b,c,d,e,f,g,h,i,j\n" + row * (1024 * 1024 // len(row) + 100)
    response = upload(client, content, "big.csv")
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_upload_detects_semicolon_delimiter_and_cp1252(client):
    content = "name;amount\nCafé;1,50\nThé;2,00\n".encode("cp1252")
    response = upload(client, content, "euro.csv")
    assert response.status_code == 201
    body = response.json()
    assert body["delimiter"] == ";"
    assert body["encoding"] == "cp1252"
    preview = client.get(f"/api/datasets/{body['id']}/preview").json()
    assert preview["rows"][0][0] == "Café"


def test_untrusted_filename_is_only_used_as_display_text(client, settings):
    response = upload(client, KNOWN_CSV, "../../etc/passwd.csv")
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "passwd"
    stored = list(settings.datasets_dir.iterdir())
    assert [path.name for path in stored] == [body["id"]]


def test_duplicate_and_blank_headers_are_renamed(client):
    response = upload(client, "amount,amount,\n1,2,3\n4,5,6\n", "dup.csv")
    assert response.status_code == 201
    detail = client.get(f"/api/datasets/{response.json()['id']}").json()
    assert [column["name"] for column in detail["columns"]] == ["amount", "amount_2", "column_3"]
    assert len(detail["warnings"]) == 2


def test_list_and_detail(client, known_dataset):
    listing = client.get("/api/datasets").json()
    assert [item["id"] for item in listing] == [known_dataset]
    detail = client.get(f"/api/datasets/{known_dataset}").json()
    types = {column["name"]: column["inferred_type"] for column in detail["columns"]}
    assert types == {
        "order_id": "identifier",
        "order_date": "datetime",
        "category": "categorical",
        "region": "categorical",
        "quantity": "numeric",
        "unit_price": "numeric",
        "revenue": "numeric",
    }
    assert detail["roles"]["revenue"] == "revenue"
    assert detail["roles"]["date"] == "order_date"


def test_preview_pagination(client, known_dataset):
    body = client.get(f"/api/datasets/{known_dataset}/preview", params={"offset": 2, "limit": 2}).json()
    assert body["total_rows"] == 6
    assert body["rows"] == [
        ["3", "2025-02-03", "A", "North", "3", "10", "30"],
        ["4", "2025-02-15", "A", "South", "1", "50", "50"],
    ]


def test_preview_validates_limits(client, known_dataset):
    response = client.get(f"/api/datasets/{known_dataset}/preview", params={"limit": 1000})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


def test_rename_dataset(client, known_dataset):
    response = client.patch(f"/api/datasets/{known_dataset}", json={"name": "  Renamed   data "})
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed data"


def test_delete_dataset_removes_files(client, known_dataset, settings):
    assert (settings.datasets_dir / known_dataset).is_dir()
    assert client.delete(f"/api/datasets/{known_dataset}").status_code == 204
    assert not (settings.datasets_dir / known_dataset).exists()
    assert client.get(f"/api/datasets/{known_dataset}").status_code == 404


def test_invalid_identifier_is_rejected(client):
    assert client.get("/api/datasets/..%2F..%2Fetc").status_code in (404, 422)
    assert client.get("/api/datasets/not-an-id").status_code == 422


def test_sample_dataset_uses_import_pipeline(client):
    response = client.post("/api/datasets/sample")
    assert response.status_code == 201
    body = response.json()
    assert body["is_sample"] is True
    assert body["row_count"] > 1000
    quality = client.get(f"/api/datasets/{body['id']}/quality").json()
    rules = {finding["rule"] for finding in quality["findings"]}
    assert {"duplicate_rows", "invalid_dates", "inconsistent_categories", "missing_values"} <= rules


def test_column_mapping_override(client, known_dataset):
    response = client.put(
        f"/api/datasets/{known_dataset}/column-mapping", json={"mapping": {"revenue": "", "region": "category"}}
    )
    assert response.status_code == 200
    roles = response.json()["roles"]
    assert roles["revenue"] is None
    assert roles["region"] == "category"
    analysis = client.get(f"/api/datasets/{known_dataset}/analysis").json()
    assert analysis["revenue_source"] == "derived"


def test_column_mapping_rejects_incompatible_column(client, known_dataset):
    response = client.put(f"/api/datasets/{known_dataset}/column-mapping", json={"mapping": {"revenue": "category"}})
    assert response.status_code == 422


def test_export_working_copy_neutralises_formulas(client):
    response = upload(client, 'name,value\n=HYPERLINK("x"),-5\n@cmd,3\n', "formula.csv")
    exported = client.get(f"/api/datasets/{response.json()['id']}/export.csv").text
    assert "'=HYPERLINK" in exported
    assert "'@cmd" in exported
    assert ",-5" in exported
