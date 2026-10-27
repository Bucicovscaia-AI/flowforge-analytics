"""Make.com webhook client, using a mock HTTP transport (no network)."""

import json
from dataclasses import replace

import httpx2
import pytest

from app.services.webhook import WebhookError, build_report_payload, describe_target, send_event

URL = "https://hook.eu1.make.com/abc123secret"


@pytest.fixture
def hook_settings(settings):
    return replace(settings, make_webhook_url=URL, make_webhook_api_key="k-123")


def transport(handler, calls):
    def wrapped(request):
        calls.append(request)
        return handler(request)

    return httpx2.MockTransport(wrapped)


def test_not_configured_raises(settings):
    with pytest.raises(WebhookError, match="not configured"):
        send_event({"event": "test.ping"}, settings)


def test_http_url_is_refused(hook_settings):
    with pytest.raises(WebhookError, match="https"):
        send_event({"event": "test.ping"}, replace(hook_settings, make_webhook_url="http://hook.make.com/x"))


def test_successful_delivery_sends_json_and_api_key(hook_settings):
    calls = []
    result = send_event({"event": "test.ping"}, hook_settings, transport(lambda r: httpx2.Response(200, text="Accepted"), calls))
    assert result["delivered"] and result["status_code"] == 200 and result["response"] == "Accepted"
    body = json.loads(calls[0].content)
    assert body["event"] == "test.ping" and body["source"] == "flowforge-analytics" and body["event_id"]
    assert calls[0].headers["x-make-apikey"] == "k-123"


def test_server_error_is_retried_once(hook_settings, monkeypatch):
    monkeypatch.setattr("app.services.webhook.time.sleep", lambda s: None)
    calls = []
    responses = iter([httpx2.Response(503), httpx2.Response(200, text="Accepted")])
    result = send_event({"event": "x"}, hook_settings, transport(lambda r: next(responses), calls))
    assert result["attempts"] == 2 and len(calls) == 2


def test_client_error_is_not_retried(hook_settings):
    calls = []
    with pytest.raises(WebhookError, match="HTTP 410"):
        send_event({"event": "x"}, hook_settings, transport(lambda r: httpx2.Response(410), calls))
    assert len(calls) == 1


def test_timeout_reports_readable_error(hook_settings, monkeypatch):
    monkeypatch.setattr("app.services.webhook.time.sleep", lambda s: None)

    def boom(request):
        raise httpx2.ReadTimeout("timed out", request=request)

    with pytest.raises(WebhookError, match="did not respond"):
        send_event({"event": "x"}, hook_settings, transport(boom, []))


def test_target_description_hides_secret_path(hook_settings):
    assert describe_target(hook_settings) == "hook.eu1.make.com"


def test_report_payload_has_aggregates_only(client):
    from tests.conftest import VALID_CSV, upload

    analysis = upload(client, VALID_CSV).json()
    report = {"id": "rpt_000000000001", "title": "T", "created_at": "2026-10-27T00:00:00+00:00"}
    payload = build_report_payload(report, analysis, None)
    assert payload["event"] == "report.generated"
    assert payload["kpis"]["total_revenue"] == 205.0
    assert payload["top_category"]["name"] == "Clothing"
    assert payload["insight_source"] == "rule-based"
    assert "preview" not in json.dumps(payload) and "A1" not in json.dumps(payload)
