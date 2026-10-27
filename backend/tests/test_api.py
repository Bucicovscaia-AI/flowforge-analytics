"""End-to-end API tests: upload -> analysis -> insights -> report -> history."""

from dataclasses import replace

import httpx2
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import VALID_CSV, upload


def test_valid_upload_returns_full_analysis(client):
    response = upload(client, VALID_CSV)
    assert response.status_code == 201
    body = response.json()
    assert body["id"].startswith("ana_")
    assert body["dataset"]["file_name"] == "orders.csv"
    assert body["quality"]["rows_received"] == 5
    assert body["kpis"]["summary"]["total_revenue"] == 205.0
    assert len(body["cleaning_steps"]) == 8
    assert body["preview"]["rows"][0]["order_id"] == "A1"
    # Stored and retrievable.
    assert client.get(f"/api/analyses/{body['id']}").json()["id"] == body["id"]
    assert client.get("/api/analyses").json()[0]["id"] == body["id"]


def test_upload_records_synthetic_flag(client):
    assert upload(client, VALID_CSV, synthetic=False).json()["dataset"]["synthetic"] is False


def test_upload_reports_missing_values_and_duplicates(client):
    csv = VALID_CSV + "A4,2026-02-14,Jacket,Clothing,South,Phone,Business,2,50.00\nA5,2026-02-15,Mug,Home,,Online,New,1,\n"
    body = upload(client, csv).json()
    assert body["quality"]["duplicate_rows"] == 1
    assert body["quality"]["rows_removed"] == 2  # the duplicate and the row without a price
    assert body["profile"]["missing_cells"] == 3  # customer_type blank, region blank, unit_price blank


@pytest.mark.parametrize(
    "content, name, content_type, status, fragment",
    [
        (VALID_CSV, "orders.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 415, "not a CSV"),
        (VALID_CSV, "orders.csv", "application/pdf", 415, "not accepted"),
        ("", "orders.csv", "text/csv", 400, "empty"),
        ("order_id,order_date,quantity,unit_price\n", "orders.csv", "text/csv", 422, "no data rows"),
        ("order_id,product\nA1,Lamp\n", "orders.csv", "text/csv", 422, "Required columns are missing"),
        ('order_id,order_date,quantity,unit_price\nA1,"2026,1,2\n', "orders.csv", "text/csv", 422, "malformed"),
    ],
)
def test_invalid_uploads_return_readable_errors(client, content, name, content_type, status, fragment):
    response = upload(client, content, name=name, content_type=content_type)
    assert response.status_code == status
    detail = response.json()["detail"]
    assert fragment in detail["message"]
    assert detail["problems"]


def test_oversized_upload_is_rejected(client):
    big = VALID_CSV + "A9,2026-01-01,Lamp,Home,North,Online,New,1,1.00\n" * 30000  # > 1 MB test limit
    response = upload(client, big)
    assert response.status_code == 413


def test_upload_without_file_is_a_validation_error(client):
    response = client.post("/api/datasets/upload", data={"synthetic": "true"})
    assert response.status_code == 422


def test_sample_datasets_are_listed_and_analysed(client):
    samples = client.get("/api/samples").json()
    assert {s["id"] for s in samples} == {"retail-2026", "web-minimal"}
    assert all(s["synthetic"] for s in samples)
    body = client.post("/api/samples/retail-2026/analyse").json()
    assert body["dataset"]["synthetic"] is True
    assert body["quality"]["duplicate_rows"] == 15
    assert body["kpis"]["unavailable"] == []
    minimal = client.post("/api/samples/web-minimal/analyse").json()
    assert {u["kpi"] for u in minimal["kpis"]["unavailable"]} >= {"revenue_by_region", "revenue_by_category"}


def test_unknown_sample_and_analysis_return_404(client):
    assert client.post("/api/samples/nope/analyse").status_code == 404
    assert client.get("/api/analyses/ana_000000000000").status_code == 404
    assert client.get("/api/analyses/../../etc").status_code == 404


def test_insights_without_ai_key_use_labelled_fallback(client):
    analysis = upload(client, VALID_CSV).json()
    result = client.post(f"/api/analyses/{analysis['id']}/insights").json()
    assert result["source"] == "rule-based"
    assert client.get(f"/api/analyses/{analysis['id']}").json()["insights"]["source"] == "rule-based"
    payload = client.get(f"/api/analyses/{analysis['id']}/ai-payload").json()
    assert set(payload) == {"dataset", "data_quality", "kpis", "breakdowns", "unavailable_kpis"}


def test_report_generation_download_history_and_delete(client):
    analysis = upload(client, VALID_CSV).json()
    response = client.post("/api/reports", json={"analysis_id": analysis["id"], "title": "Q1 review"})
    assert response.status_code == 201
    report = response.json()
    assert report["title"] == "Q1 review" and report["synthetic"] is True
    assert report["webhook"]["status"] == "not_configured"

    pdf = client.get(f"/api/reports/{report['id']}/download")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-")
    assert "attachment" in pdf.headers["content-disposition"]

    assert [r["id"] for r in client.get("/api/reports").json()] == [report["id"]]
    assert client.delete(f"/api/reports/{report['id']}").status_code == 204
    assert client.get("/api/reports").json() == []
    assert client.get(f"/api/reports/{report['id']}/download").status_code == 404


def test_report_pdf_contains_analysis_figures(client):
    pypdf = pytest.importorskip("pypdf")
    import io

    analysis = upload(client, VALID_CSV).json()
    report = client.post("/api/reports", json={"analysis_id": analysis["id"]}).json()
    pdf = client.get(f"/api/reports/{report['id']}/download").content
    text = "".join(page.extract_text() for page in pypdf.PdfReader(io.BytesIO(pdf)).pages)
    for expected in ["Dataset overview", "Data-quality summary", "£205.00", "Synthetic data", "Limitations and assumptions", "not AI-generated"]:
        assert expected in text


def test_report_for_unknown_analysis_is_404(client):
    assert client.post("/api/reports", json={"analysis_id": "ana_000000000000"}).status_code == 404


def test_report_request_validation(client):
    assert client.post("/api/reports", json={}).status_code == 422
    assert client.post("/api/reports", json={"analysis_id": "x", "title": "t" * 200}).status_code == 422


def test_webhook_endpoints_when_not_configured(client):
    assert client.post("/api/integrations/make/test").status_code == 409
    analysis = upload(client, VALID_CSV).json()
    report = client.post("/api/reports", json={"analysis_id": analysis["id"], "notify_make": True}).json()
    assert report["webhook"]["status"] == "not_configured"
    assert client.post(f"/api/reports/{report['id']}/notify").status_code == 409


def test_report_notifies_make_when_configured(settings, monkeypatch):
    sent = []

    def fake_send(payload, s, transport=None):
        sent.append(payload)
        return {"delivered": True, "status_code": 200, "event_id": "e1", "response": "Accepted", "attempts": 1}

    monkeypatch.setattr("app.routers.reports.send_event", fake_send)
    client = TestClient(create_app(replace(settings, make_webhook_url="https://hook.eu1.make.com/secret")))
    analysis = upload(client, VALID_CSV).json()
    report = client.post("/api/reports", json={"analysis_id": analysis["id"], "notify_make": True}).json()
    assert report["webhook"]["status"] == "delivered"
    assert sent[0]["event"] == "report.generated"
    assert client.get("/api/reports").json()[0]["webhook"]["status"] == "delivered"
    config = client.get("/api/config").json()
    assert config["webhook"] == {"configured": True, "target_host": "hook.eu1.make.com", "api_key_set": False}
    assert "secret" not in str(config)


def test_config_never_exposes_secrets(settings):
    client = TestClient(create_app(replace(settings, ai_api_key="sk-test-secret", make_webhook_url="https://hook.make.com/xyz", make_webhook_api_key="k")))
    text = client.get("/api/config").text
    assert "sk-test-secret" not in text and "xyz" not in text
    assert client.get("/api/config").json()["ai"]["configured"] is True


def test_unknown_api_route_is_404_even_with_frontend_build(settings, tmp_path):
    static = tmp_path / "dist"
    static.mkdir()
    (static / "index.html").write_text("<html>app</html>")
    client = TestClient(create_app(replace(settings, static_dir=static)))
    assert client.get("/api/nope").status_code == 404
    assert client.get("/reports").text == "<html>app</html>"  # client-side route
    assert client.get("/../../etc/passwd").status_code in (200, 404)
    assert "root:" not in client.get("/..%2F..%2Fetc%2Fpasswd").text
