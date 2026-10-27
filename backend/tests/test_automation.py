import hashlib
import hmac
import json

import httpx

from app.integrations.make_webhook import MakeWebhookClient, webhook_url_problem
from tests.conftest import KNOWN_CSV, upload

WEBHOOK_URL = "https://hook.eu1.make.com/test-token"


def webhook(handler, secret=""):
    return MakeWebhookClient(WEBHOOK_URL, secret=secret, timeout_seconds=2, transport=httpx.MockTransport(handler))


def test_status_when_not_configured(client):
    status = client.get("/api/automation/status").json()
    assert status["configured"] is False
    assert status["configuration_problem"] == "MAKE_WEBHOOK_URL is not set."


def test_trigger_without_configuration_is_refused(client, known_dataset):
    response = client.post("/api/automation/trigger", json={"event_type": "dataset.analysed", "dataset_id": known_dataset})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "automation_not_configured"
    assert client.get("/api/automation/runs").json() == []


def test_webhook_url_must_use_https():
    assert webhook_url_problem("http://hook.make.com/x") == "MAKE_WEBHOOK_URL must use HTTPS."
    assert webhook_url_problem("https://hook.make.com/x") is None


def test_successful_delivery_sends_summary_and_signature(make_client):
    received = {}

    def handler(request: httpx.Request) -> httpx.Response:
        received["body"] = request.content
        received["signature"] = request.headers.get("X-FlowForge-Signature")
        return httpx.Response(200, text="Accepted")

    client = make_client(make_webhook_url=WEBHOOK_URL, webhook_client=webhook(handler, secret="s3cret"))
    dataset_id = upload(client, KNOWN_CSV).json()["id"]
    run = client.post("/api/automation/trigger", json={"event_type": "dataset.analysed", "dataset_id": dataset_id}).json()

    assert run["status"] == "delivered"
    assert run["http_status"] == 200
    payload = json.loads(received["body"])
    assert payload["event"] == "dataset.analysed"
    assert payload["trigger"] == "manual"
    assert payload["dataset"]["record_count"] == 6
    assert payload["summary"]["total_revenue"] == 230.0
    assert "rows" not in payload and "2025-01-20" not in received["body"].decode()
    expected = "sha256=" + hmac.new(b"s3cret", received["body"], hashlib.sha256).hexdigest()
    assert received["signature"] == expected

    runs = client.get("/api/automation/runs").json()
    assert [item["id"] for item in runs] == [run["id"]]


def test_failed_delivery_is_reported(make_client):
    client = make_client(make_webhook_url=WEBHOOK_URL, webhook_client=webhook(lambda request: httpx.Response(410)))
    run = client.post("/api/automation/trigger", json={"event_type": "automation.test"}).json()
    assert run["status"] == "failed"
    assert run["http_status"] == 410
    assert "no longer active" in run["message"]


def test_network_errors_and_timeouts_are_reported(make_client):
    def timeout(request):
        raise httpx.ReadTimeout("timed out", request=request)

    def unreachable(request):
        raise httpx.ConnectError("refused", request=request)

    for handler, text in ((timeout, "did not respond"), (unreachable, "could not be reached")):
        client = make_client(make_webhook_url=WEBHOOK_URL, webhook_client=webhook(handler))
        run = client.post("/api/automation/trigger", json={"event_type": "automation.test"}).json()
        assert run["status"] == "failed"
        assert text in run["message"]


def test_report_event_and_payload_preview(make_client):
    client = make_client(
        make_webhook_url=WEBHOOK_URL,
        public_base_url="https://flowforge.example.com",
        webhook_client=webhook(lambda request: httpx.Response(200)),
    )
    dataset_id = upload(client, KNOWN_CSV).json()["id"]
    report_id = client.post("/api/reports", json={"dataset_id": dataset_id}).json()["id"]
    preview = client.post("/api/automation/preview", json={"event_type": "report.generated", "report_id": report_id}).json()
    assert preview["report"]["id"] == report_id
    assert preview["report"]["download_url"].startswith("https://flowforge.example.com/api/reports/")
    assert client.get("/api/automation/runs").json() == []  # preview does not send

    missing = client.post("/api/automation/trigger", json={"event_type": "report.generated"})
    assert missing.status_code == 422


def test_rule_triggers_on_report_only_when_enabled(make_client):
    sent = []
    handler = lambda request: (sent.append(json.loads(request.content)), httpx.Response(200))[1]  # noqa: E731
    disabled = make_client(make_webhook_url=WEBHOOK_URL, webhook_client=webhook(handler))
    dataset_id = upload(disabled, KNOWN_CSV).json()["id"]
    assert disabled.post("/api/reports", json={"dataset_id": dataset_id}).json()["automation_run"] is None
    assert sent == []

    enabled = make_client(make_webhook_url=WEBHOOK_URL, automation_trigger_on_report=True, webhook_client=webhook(handler))
    report = enabled.post("/api/reports", json={"dataset_id": dataset_id}).json()
    assert report["automation_run"]["status"] == "delivered"
    assert report["automation_run"]["trigger"] == "rule"
    assert sent[0]["event"] == "report.generated"


def test_invalid_event_type_rejected(client):
    response = client.post("/api/automation/trigger", json={"event_type": "rm"})
    assert response.status_code == 422
