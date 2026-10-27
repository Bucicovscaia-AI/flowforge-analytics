"""Rule-based observations and the optional AI insights service."""

from dataclasses import replace
from types import SimpleNamespace

import anthropic
import httpx2

from app.services.ai_insights import AIInsight, AIInsightResponse, build_ai_summary, generate_insights
from app.services.observations import build_observations
from tests.conftest import VALID_CSV, upload


def make_analysis(client):
    return upload(client, VALID_CSV).json()


def test_observations_are_backed_by_kpi_figures(client):
    analysis = make_analysis(client)
    obs = build_observations(analysis["kpis"], analysis["quality"])
    titles = [o["title"] for o in obs]
    assert "Clothing is the largest category" in titles
    trend = next(o for o in obs if o["kind"] == "trend")
    assert "Jan 2026" in trend["evidence"] and "Feb 2026" in trend["evidence"]
    assert all(o["evidence"] and o["recommendation"] for o in obs)


def test_observations_mention_unavailable_kpis():
    kpis = {"summary": {}, "breakdowns": {}, "unavailable": [{"kpi": "revenue_by_region", "label": "Revenue by region", "missing_columns": ["region"]}]}
    obs = build_observations(kpis, {"rows_received": 10, "rows_removed": 0, "duplicate_rows": 0})
    assert any("Revenue by region could not be calculated" == o["title"] for o in obs)


def test_ai_summary_contains_no_raw_rows(client):
    analysis = make_analysis(client)
    payload = build_ai_summary(analysis)
    text = str(payload)
    assert "preview" not in payload
    assert not any(f"'A{i}'" in text for i in range(1, 5))  # no order ids, so no rows
    assert payload["kpis"]["total_revenue"] == analysis["kpis"]["summary"]["total_revenue"]


def test_without_api_key_returns_labelled_rule_based_fallback(client, settings):
    analysis = make_analysis(client)
    result = generate_insights(analysis, settings)
    assert result["source"] == "rule-based"
    assert result["model"] is None
    assert "not AI-generated" in result["notice"]
    assert result["insights"]


class FakeMessages:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response, error, []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def fake_client(**kwargs):
    return SimpleNamespace(messages=FakeMessages(**kwargs))


def test_ai_response_is_returned_and_labelled(client, settings):
    analysis = make_analysis(client)
    parsed = AIInsightResponse(
        summary="Revenue rose.",
        insights=[AIInsight(title="Clothing leads", evidence="£150 of £205", recommendation="Stock jackets", kind="mix")],
        caveats=["Small sample"],
    )
    fake = fake_client(response=SimpleNamespace(stop_reason="end_turn", parsed_output=parsed, model="claude-opus-5-5"))
    result = generate_insights(analysis, replace(settings, ai_api_key="test-key"), client=fake)
    assert result["source"] == "ai"
    assert result["model"] == "claude-opus-5-5"
    assert result["insights"][0]["title"] == "Clothing leads"
    sent = fake.messages.calls[0]["messages"][0]["content"]
    assert "Aggregated dataset summary" in sent and "A1" not in sent  # no order ids sent


def test_ai_refusal_falls_back(client, settings):
    analysis = make_analysis(client)
    fake = fake_client(response=SimpleNamespace(stop_reason="refusal", parsed_output=None, model="x"))
    assert generate_insights(analysis, settings, client=fake)["source"] == "rule-based"


def test_ai_api_errors_fall_back_with_reason(client, settings):
    analysis = make_analysis(client)
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    errors = {
        "rejected the API key": anthropic.AuthenticationError("bad key", response=httpx2.Response(401, request=request), body=None),
        "rate-limited": anthropic.RateLimitError("slow down", response=httpx2.Response(429, request=request), body=None),
        "could not be reached": anthropic.APIConnectionError(request=request),
        "returned an error (500)": anthropic.InternalServerError("boom", response=httpx2.Response(500, request=request), body=None),
    }
    for reason, error in errors.items():
        result = generate_insights(analysis, settings, client=fake_client(error=error))
        assert result["source"] == "rule-based"
        assert reason in result["notice"]


def test_real_sdk_request_shape_with_mocked_http(client, settings):
    """Runs the real Anthropic SDK against a mocked HTTP endpoint, checking
    the structured-output request and the parsing of the reply."""
    import json

    analysis = make_analysis(client)
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        reply = {"summary": "Revenue grew.", "insights": [{"title": "T", "evidence": "E", "recommendation": "R", "kind": "trend"}], "caveats": ["Synthetic"]}
        return httpx2.Response(
            200,
            json={
                "id": "msg_1", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
                "content": [{"type": "text", "text": json.dumps(reply)}],
                "stop_reason": "end_turn", "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    sdk = anthropic.Anthropic(api_key="test", http_client=httpx2.Client(transport=httpx2.MockTransport(handler)))
    result = generate_insights(analysis, replace(settings, ai_api_key="test"), client=sdk)
    assert result["source"] == "ai" and result["caveats"] == ["Synthetic"]
    body = seen["body"]
    assert body["model"] == settings.ai_model
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert "preview" not in body["messages"][0]["content"]
