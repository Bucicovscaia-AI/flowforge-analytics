import json

from tests.conftest import KNOWN_CSV, upload


def create_report(client, dataset_id, **extra):
    response = client.post("/api/reports", json={"dataset_id": dataset_id, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def test_generate_report_from_actual_data(client, known_dataset):
    report = create_report(client, known_dataset, title="Quarter review")
    assert report["status"] == "completed"
    assert report["title"] == "Quarter review"
    assert set(report["formats"]) == {"html", "pdf", "csv", "json"}
    assert report["record_count"] == 6
    assert report["insight_mode"] == "rule_based"

    content = client.get(f"/api/reports/{report['id']}/content").json()
    total = next(metric for metric in content["metrics"] if metric["key"] == "total_revenue")
    assert total["value"] == 230.0
    assert content["dataset"]["name"] == "known"
    assert content["insights"]["mode"] == "rule_based"
    assert content["limitations"]


def test_report_downloads(client, known_dataset):
    report = create_report(client, known_dataset)
    html = client.get(f"/api/reports/{report['id']}/download", params={"format": "html"})
    assert html.status_code == 200
    assert html.headers["content-type"].startswith("text/html")
    assert "attachment" in html.headers["content-disposition"]
    assert "230.00" in html.text
    assert "default-src 'none'" in html.headers["content-security-policy"]

    pdf = client.get(f"/api/reports/{report['id']}/download", params={"format": "pdf"})
    assert pdf.content.startswith(b"%PDF")

    csv_text = client.get(f"/api/reports/{report['id']}/download", params={"format": "csv"}).text
    assert csv_text.splitlines()[0] == "section,item,measure,value,detail"
    assert "metrics,Total revenue,currency,230.0" in csv_text

    data = client.get(f"/api/reports/{report['id']}/download", params={"format": "json"}).json()
    assert data["id"] == report["id"]

    assert client.get(f"/api/reports/{report['id']}/download", params={"format": "docx"}).status_code == 422


def test_report_html_escapes_dataset_text(client):
    dataset_id = upload(client, "category,revenue\n<script>alert(1)</script>,5\nSafe,6\n", "xss.csv").json()["id"]
    report = create_report(client, dataset_id)
    html = client.get(f"/api/reports/{report['id']}/download", params={"format": "html"}).text
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_report_history_and_deletion(client, known_dataset):
    first = create_report(client, known_dataset, title="First")
    second = create_report(client, known_dataset, title="Second")
    history = client.get("/api/reports").json()
    assert [item["id"] for item in history] == [second["id"], first["id"]]
    filtered = client.get("/api/reports", params={"dataset_id": known_dataset}).json()
    assert len(filtered) == 2

    assert client.delete(f"/api/reports/{first['id']}").status_code == 204
    assert client.get(f"/api/reports/{first['id']}").status_code == 404
    assert [item["id"] for item in client.get("/api/reports").json()] == [second["id"]]


def test_report_history_persists_after_restart(make_client):
    first_client = make_client()
    dataset_id = upload(first_client, KNOWN_CSV).json()["id"]
    report = create_report(first_client, dataset_id)

    restarted = make_client()
    assert [item["id"] for item in restarted.get("/api/reports").json()] == [report["id"]]
    assert restarted.get(f"/api/reports/{report['id']}/download", params={"format": "pdf"}).status_code == 200
    assert restarted.get(f"/api/datasets/{dataset_id}").status_code == 200


def test_report_survives_dataset_deletion(client, known_dataset):
    report = create_report(client, known_dataset)
    client.delete(f"/api/datasets/{known_dataset}")
    assert client.get(f"/api/reports/{report['id']}/download", params={"format": "html"}).status_code == 200


def test_report_for_unknown_dataset(client):
    response = client.post("/api/reports", json={"dataset_id": "0" * 32})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "dataset_not_found"


def test_report_request_validation(client):
    response = client.post("/api/reports", json={"dataset_id": "short"})
    assert response.status_code == 422
    assert response.json()["error"]["details"]["problems"][0]["field"] == "dataset_id"


def test_sample_report_is_labelled_synthetic(client):
    dataset_id = client.post("/api/datasets/sample").json()["id"]
    report = create_report(client, dataset_id)
    content = client.get(f"/api/reports/{report['id']}/content").json()
    assert content["limitations"][0].startswith("This report uses synthetic demonstration data")
    assert json.dumps(content["dataset"]).count('"is_sample": true') == 1
