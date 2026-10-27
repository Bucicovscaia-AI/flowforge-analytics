import json

import anthropic
import httpx2
import pytest

from app.engine.insights import generate_rule_based_insights
from app.integrations.ai.anthropic_provider import AnthropicInsightProvider
from app.integrations.ai.base import AIProviderError
from app.services.insights import build_ai_summary
from tests.conftest import KNOWN_CSV, upload


class FakeProvider:
    name = "anthropic"
    model = "test-model"

    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.received = None

    def generate(self, summary):
        self.received = summary
        if self.error:
            raise self.error
        return self.payload


AI_PAYLOAD = {
    "insights": [
        {
            "category": "performance",
            "kind": "interpretation",
            "title": "Category B leads",
            "statement": "Category B contributes the larger share of revenue.",
            "evidence": [{"label": "B revenue", "value": "130.00"}],
            "caveat": "",
        }
    ],
    "limitations": ["Only three months of data."],
}


def test_rule_based_insights_without_ai_credentials(client, known_dataset):
    body = client.post(f"/api/datasets/{known_dataset}/insights", json={"use_ai": True}).json()
    assert body["mode"] == "rule_based"
    assert any("No AI provider is configured" in notice for notice in body["notices"])
    assert body["insights"], "rule-based insights expected for a business dataset"
    assert all(item["source"] == "rule_based" for item in body["insights"])
    top = next(item for item in body["insights"] if item["id"] == "top-category")
    assert "56.5%" in top["statement"]
    assert top["kind"] == "fact"


def test_ai_insights_are_combined_with_measured_facts(make_client):
    provider = FakeProvider(payload=AI_PAYLOAD)
    client = make_client(insight_provider=provider)
    dataset_id = upload(client, KNOWN_CSV).json()["id"]
    body = client.post(f"/api/datasets/{dataset_id}/insights", json={"use_ai": True}).json()
    assert body["mode"] == "ai"
    assert body["model"] == "test-model"
    sources = {item["source"] for item in body["insights"]}
    assert sources == {"ai", "rule_based"}
    assert all(item["kind"] == "fact" for item in body["insights"] if item["source"] == "rule_based")
    assert "Only three months of data." in body["limitations"]
    assert body["data_sent"]


def test_ai_summary_contains_no_raw_rows(make_client):
    provider = FakeProvider(payload=AI_PAYLOAD)
    client = make_client(insight_provider=provider)
    secret_ids = "".join(f"CUST-SECRET-{n},2025-01-{n + 1:02d},A,{n}\n" for n in range(30))
    dataset_id = upload(client, "customer_ref,order_date,category,revenue\n" + secret_ids).json()["id"]
    client.post(f"/api/datasets/{dataset_id}/insights", json={"use_ai": True})
    assert "CUST-SECRET" not in json.dumps(provider.received)


def test_ai_failure_falls_back_to_rule_based(make_client):
    provider = FakeProvider(error=AIProviderError("rate_limited", "Rate limit reached."))
    client = make_client(insight_provider=provider)
    dataset_id = upload(client, KNOWN_CSV).json()["id"]
    body = client.post(f"/api/datasets/{dataset_id}/insights", json={"use_ai": True}).json()
    assert body["mode"] == "rule_based"
    assert body["ai_error"] == "rate_limited"
    assert any("Rate limit reached." in notice for notice in body["notices"])


def test_ai_returning_nothing_usable_falls_back(make_client):
    client = make_client(insight_provider=FakeProvider(payload={"insights": [{"title": ""}], "limitations": []}))
    dataset_id = upload(client, KNOWN_CSV).json()["id"]
    body = client.post(f"/api/datasets/{dataset_id}/insights", json={"use_ai": True}).json()
    assert body["mode"] == "rule_based"
    assert body["ai_error"] == "invalid_response"


def test_use_ai_false_skips_provider(make_client):
    provider = FakeProvider(payload=AI_PAYLOAD)
    client = make_client(insight_provider=provider)
    dataset_id = upload(client, KNOWN_CSV).json()["id"]
    body = client.post(f"/api/datasets/{dataset_id}/insights", json={"use_ai": False}).json()
    assert body["mode"] == "rule_based"
    assert provider.received is None


def test_no_insights_explained_when_nothing_to_say(client):
    dataset_id = upload(client, "note\nhello there\n").json()["id"]
    body = client.post(f"/api/datasets/{dataset_id}/insights", json={"use_ai": False}).json()
    assert body["insights"] == []
    assert any("No insights could be produced" in notice for notice in body["notices"])


def test_rule_based_insights_do_not_invent_trend_without_dates():
    analysis = {"metrics": [], "breakdowns": {}, "correlations": [], "roles": {}, "time_series": None}
    quality = {"findings": [], "score": 100, "grade": "Excellent"}
    assert generate_rule_based_insights(analysis, quality) == []


class _Request:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def _status_error(cls, status):
    response = httpx2.Response(status, request=_Request.request, json={"error": {"type": "x", "message": "x"}})
    return cls(message="error", response=response, body=None)


class FakeMessages:
    def __init__(self, error=None, response=None):
        self.error = error
        self.response = response
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, messages):
        self.messages = messages


@pytest.mark.parametrize(
    "error, reason",
    [
        (_status_error(anthropic.AuthenticationError, 401), "authentication"),
        (_status_error(anthropic.RateLimitError, 429), "rate_limited"),
        (_status_error(anthropic.InternalServerError, 500), "unavailable"),
        (anthropic.APIConnectionError(request=_Request.request), "unavailable"),
        (anthropic.APITimeoutError(request=_Request.request), "timeout"),
    ],
)
def test_anthropic_provider_maps_errors(error, reason):
    provider = AnthropicInsightProvider("key", "model", 5, 1000, client=FakeClient(FakeMessages(error=error)))
    with pytest.raises(AIProviderError) as raised:
        provider.generate({"metrics": []})
    assert raised.value.reason == reason


class _Block:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _Response:
    def __init__(self, text, stop_reason="end_turn"):
        self.content = [_Block(text)]
        self.stop_reason = stop_reason


def test_anthropic_provider_parses_structured_output_and_sends_summary_only():
    messages = FakeMessages(response=_Response(json.dumps(AI_PAYLOAD)))
    provider = AnthropicInsightProvider("key", "claude-test", 5, 1000, client=FakeClient(messages))
    result = provider.generate({"metrics": [{"label": "Total revenue", "value": 230}]})
    assert result == AI_PAYLOAD
    assert messages.kwargs["model"] == "claude-test"
    assert messages.kwargs["output_config"]["format"]["type"] == "json_schema"
    assert "Total revenue" in messages.kwargs["messages"][0]["content"]


@pytest.mark.parametrize("stop_reason, text", [("refusal", "{}"), ("end_turn", "not json"), ("max_tokens", "{")])
def test_anthropic_provider_rejects_unusable_responses(stop_reason, text):
    provider = AnthropicInsightProvider(
        "key", "m", 5, 1000, client=FakeClient(FakeMessages(response=_Response(text, stop_reason)))
    )
    with pytest.raises(AIProviderError):
        provider.generate({})


def test_build_ai_summary_limits_groups():
    analysis = {
        "breakdowns": {
            "product": {
                "column": "product",
                "measure": "revenue",
                "total_groups": 30,
                "rows": [{"group": f"P{n}", "records": 1, "revenue": 1.0, "share": 1.0} for n in range(30)],
            }
        },
        "metrics": [],
        "columns": [],
        "roles": {},
    }
    summary = build_ai_summary(analysis, {"findings": []})
    assert len(summary["breakdowns"]["product"]["top_groups"]) == 10
