"""End-to-end behaviour of report delivery through Make.com: payload, signed PDF link and confirmation."""

import json
import sqlite3
from urllib.parse import urlparse

import httpx

from app.integrations.make_webhook import MakeWebhookClient
from app.integrations.signed_links import LinkSigner
from app.storage.database import Database
from tests.conftest import KNOWN_CSV, upload

WEBHOOK_URL = "https://hook.eu1.make.com/test-token"
BASE_URL = "https://flowforge.example.com"


class Recorder:
    def __init__(self, status: int = 200):
        self.status = status
        self.payloads: list[dict] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.payloads.append(json.loads(request.content))
        return httpx.Response(self.status, text="Accepted")


def setup(make_client, recorder=None, **overrides):
    recorder = recorder or Recorder()
    overrides = {"make_webhook_url": WEBHOOK_URL, "public_base_url": BASE_URL, **overrides}
    client = make_client(
        webhook_client=MakeWebhookClient(WEBHOOK_URL, timeout_seconds=2, transport=httpx.MockTransport(recorder)), **overrides
    )
    dataset_id = upload(client, KNOWN_CSV, name="Q1 orders").json()["id"]
    report = client.post("/api/reports", json={"dataset_id": dataset_id, "title": "Q1 review"}).json()
    return client, recorder, dataset_id, report["id"]


def local(url: str) -> str:
    parsed = urlparse(url)
    assert f"{parsed.scheme}://{parsed.netloc}" == BASE_URL
    return f"{parsed.path}?{parsed.query}"


def send_report(client, report_id, **extra):
    return client.post("/api/automation/trigger", json={"event_type": "report.generated", "report_id": report_id, **extra})


def test_report_event_carries_real_kpis_and_pdf_link(make_client):
    client, recorder, dataset_id, report_id = setup(make_client)
    run = send_report(client, report_id).json()
    assert run["status"] == "delivered"
    assert run["confirmation_status"] == "pending"

    payload = recorder.payloads[0]
    assert payload["event"] == "report.generated" and payload["schema_version"] == 2
    assert payload["event_id"] == run["id"]
    assert payload["dataset"] == {
        "id": dataset_id,
        "name": "Q1 orders",
        "is_sample": False,
        "record_count": 6,
        "column_count": 7,
        "quality_score": payload["dataset"]["quality_score"],
    }
    assert isinstance(payload["dataset"]["quality_score"], float)
    summary = payload["summary"]
    assert summary["total_revenue"] == 230.0 and isinstance(summary["total_revenue"], float)
    assert summary["records"] == 6 and isinstance(summary["records"], int)
    assert summary["average_transaction_value"] == 38.33
    assert summary["date_range"] == {"start": "2025-01-05", "end": "2025-03-31"}
    kpis = {item["key"]: item for item in payload["kpis"]}
    assert kpis["total_revenue"]["display"] == "230.00"
    assert kpis["date_range"]["display"] == "2025-01-05 to 2025-03-31"
    assert "<strong>Total revenue:</strong> 230.00" in payload["kpi_summary_html"]

    pdf = payload["report"]["pdf"]
    assert pdf["available"] is True
    assert pdf["filename"] == "q1-review.pdf"
    assert pdf["content_type"] == "application/pdf"
    response = client.get(local(pdf["download_url"]))
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "no-store"
    assert 'filename="q1-review.pdf"' in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) == pdf["size_bytes"]

    history = client.get("/api/automation/runs").json()[0]
    assert history["pdf_downloaded_at"] is not None
    stored = json.dumps(history["payload"])
    assert "signature=redacted" in stored and pdf["download_url"] not in stored
    assert "2025-01-20" not in json.dumps(payload)  # no raw rows


def test_payload_uses_report_snapshot_after_dataset_changes(make_client):
    client, recorder, dataset_id, report_id = setup(make_client)
    assert client.delete(f"/api/datasets/{dataset_id}").status_code == 204
    run = send_report(client, report_id).json()
    assert run["status"] == "delivered"
    assert recorder.payloads[0]["summary"]["total_revenue"] == 230.0


def test_signed_links_are_checked(make_client):
    client, recorder, _, report_id = setup(make_client)
    send_report(client, report_id)
    payload = recorder.payloads[0]
    pdf_url = local(payload["report"]["pdf"]["download_url"])
    confirm_url = local(payload["delivery"]["confirmation_url"])
    run_id = payload["event_id"]

    tampered = pdf_url[:-1] + ("0" if pdf_url[-1] != "0" else "1")
    assert client.get(tampered).json()["error"]["code"] == "link_invalid"
    assert client.get(tampered).status_code == 403
    # A confirmation link cannot be used to download the PDF, and links are bound to one event.
    query = confirm_url.split("?", 1)[1]
    assert client.get(f"/api/automation/runs/{run_id}/report.pdf?{query}").status_code == 403
    assert client.get(pdf_url.replace(run_id, "0" * 32)).status_code == 403
    assert client.get(f"/api/automation/runs/{run_id}/report.pdf").status_code == 422

    signer: LinkSigner = client.app.state.services.automation.signer
    signer.clock = lambda: 4_000_000_000
    expired = client.get(pdf_url)
    assert expired.status_code == 410
    assert expired.json()["error"]["code"] == "link_expired"


def test_pdf_of_deleted_report_is_not_served(make_client):
    client, recorder, _, report_id = setup(make_client)
    send_report(client, report_id)
    assert client.delete(f"/api/reports/{report_id}").status_code == 204
    response = client.get(local(recorder.payloads[0]["report"]["pdf"]["download_url"]))
    assert response.status_code == 404


def test_confirmation_records_scenario_outcome(make_client):
    client, recorder, _, report_id = setup(make_client)
    send_report(client, report_id)
    confirm_url = local(recorder.payloads[0]["delivery"]["confirmation_url"])

    failed = client.post(confirm_url, json={"status": "failed", "message": "Gmail: invalid recipient"}).json()
    assert failed["confirmation_status"] == "failed"
    assert failed["confirmation_message"] == "Gmail: invalid recipient"
    sent = client.post(confirm_url, json={"status": "sent"}).json()
    assert sent["confirmation_status"] == "sent" and sent["confirmed_at"]
    assert client.post(confirm_url, json={"status": "delivered-maybe"}).status_code == 422
    assert client.post(confirm_url.split("?")[0], json={"status": "sent"}).status_code == 422


def test_duplicate_report_sends_need_confirmation(make_client):
    client, recorder, _, report_id = setup(make_client)
    assert send_report(client, report_id).status_code == 200
    duplicate = send_report(client, report_id)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "already_sent"
    assert len(recorder.payloads) == 1

    assert send_report(client, report_id, resend=True).json()["status"] == "delivered"
    assert len(recorder.payloads) == 2
    assert recorder.payloads[0]["event_id"] != recorder.payloads[1]["event_id"]

    # Once the scenario reports a failure, sending again does not need the extra confirmation.
    client.post(local(recorder.payloads[1]["delivery"]["confirmation_url"]), json={"status": "failed"})
    client.post(local(recorder.payloads[0]["delivery"]["confirmation_url"]), json={"status": "failed"})
    assert send_report(client, report_id).status_code == 200


def test_rejected_webhook_is_not_pending_confirmation_and_can_be_retried(make_client):
    client, recorder, _, report_id = setup(make_client, Recorder(status=500))
    run = send_report(client, report_id).json()
    assert run["status"] == "failed"
    assert run["confirmation_status"] is None
    assert send_report(client, report_id).status_code == 200  # a failed attempt is not a duplicate


def test_without_public_url_pdf_is_marked_unavailable(make_client):
    client, recorder, _, report_id = setup(make_client, public_base_url="")
    send_report(client, report_id)
    payload = recorder.payloads[0]
    assert payload["report"]["pdf"] == {
        "available": False,
        "reason": "PUBLIC_BASE_URL is not set, so FlowForge cannot build a link Make.com can reach.",
    }
    assert payload["delivery"] is None
    status = client.get("/api/automation/status").json()
    assert status["pdf_links"]["enabled"] is False


def test_test_event_contains_no_data_but_can_be_confirmed(make_client):
    client, recorder, _, _ = setup(make_client)
    client.post("/api/automation/trigger", json={"event_type": "automation.test"})
    payload = recorder.payloads[-1]
    assert payload["dataset"] is None and payload["report"] is None and payload["summary"] is None
    run = client.post(local(payload["delivery"]["confirmation_url"]), json={"status": "sent"}).json()
    assert run["confirmation_status"] == "sent"


def test_rule_survives_unexpected_send_errors(make_client):
    class Broken(MakeWebhookClient):
        def send(self, payload):
            raise RuntimeError("boom")

    client = make_client(make_webhook_url=WEBHOOK_URL, automation_trigger_on_report=True, webhook_client=Broken(WEBHOOK_URL))
    dataset_id = upload(client, KNOWN_CSV).json()["id"]
    response = client.post("/api/reports", json={"dataset_id": dataset_id})
    assert response.status_code == 201
    assert response.json()["automation_run"]["status"] == "failed"


def test_status_reports_link_settings_without_secrets(make_client):
    client, _, _, _ = setup(make_client, report_link_secret="link-secret-value")
    body = client.get("/api/automation/status").text
    status = json.loads(body)
    assert status["pdf_links"] == {"enabled": True, "problem": None, "ttl_minutes": 60, "survive_restart": True, "max_pdf_mb": 20}
    assert "link-secret-value" not in body and WEBHOOK_URL not in body


def test_existing_database_gains_new_columns(tmp_path):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """CREATE TABLE automation_runs (id TEXT PRIMARY KEY, event_type TEXT NOT NULL, trigger TEXT NOT NULL,
               dataset_id TEXT, report_id TEXT, status TEXT NOT NULL, http_status INTEGER, message TEXT NOT NULL,
               duration_ms INTEGER, payload TEXT NOT NULL, created_at TEXT NOT NULL)"""
        )
    Database(path)
    with sqlite3.connect(path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(automation_runs)")}
    assert {"pdf_downloaded_at", "confirmation_status", "confirmation_message", "confirmed_at"} <= columns


def test_render_external_url_is_used_when_no_public_url_is_set(monkeypatch):
    from app.config import load_settings

    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://flowforge-analytics.onrender.com/")
    monkeypatch.setenv("REPORT_LINK_TTL_MINUTES", "1")
    settings = load_settings()
    assert settings.public_base_url == "https://flowforge-analytics.onrender.com"
    assert settings.report_link_ttl_minutes == 5  # minimum
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://reports.example.com")
    assert load_settings().public_base_url == "https://reports.example.com"
