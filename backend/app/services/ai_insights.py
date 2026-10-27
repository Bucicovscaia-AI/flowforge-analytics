"""Optional AI-assisted insights (Anthropic Claude API).

Only an aggregated summary is sent: KPI totals, breakdown tables and
data-quality counts. Individual rows, the original file and any credentials
never leave the server.

If no API key is configured, or the call fails, the rule-based observations
are returned instead. That output is always labelled ``"source": "rule-based"``
and is never described as AI-generated.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import anthropic
from pydantic import BaseModel, Field

from app.config import Settings
from app.services.observations import build_observations

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a business analyst writing for a small-business owner.
You receive an aggregated JSON summary of a sales dataset: KPI totals, breakdown
tables and data-quality counts. You never see individual rows.

Write observations and recommendations that are supported by the numbers in the
summary. Quote the figures you rely on in each evidence field. Do not invent
figures, causes, benchmarks or external facts that are not in the summary; where a
cause is uncertain, say what should be checked. If the dataset is labelled
synthetic, treat findings as a demonstration and do not present them as real
business results. Use British English and GBP."""


class AIInsight(BaseModel):
    title: str = Field(description="Short headline, under 12 words")
    evidence: str = Field(description="The figures from the summary that support this point")
    recommendation: str = Field(description="One practical, specific next step")
    kind: str = Field(description="One of: trend, risk, opportunity, mix, concentration, data")


class AIInsightResponse(BaseModel):
    summary: str = Field(description="Two or three sentence overview of performance")
    insights: list[AIInsight] = Field(description="Four to six observations with recommendations")
    caveats: list[str] = Field(description="Limitations of this analysis")


def build_ai_summary(analysis: dict) -> dict:
    """The exact, row-free payload sent to the AI service."""
    kpis = analysis["kpis"]
    breakdowns = {k: v[:10] for k, v in kpis["breakdowns"].items()}
    return {
        "dataset": {
            "name": analysis["dataset"]["file_name"],
            "synthetic": analysis["dataset"]["synthetic"],
            "rows_received": analysis["quality"]["rows_received"],
            "rows_analysed": analysis["quality"]["rows_analysed"],
        },
        "data_quality": {
            "duplicate_rows": analysis["quality"]["duplicate_rows"],
            "missing_cells": analysis["quality"]["missing_cells"],
            "rows_removed": analysis["quality"]["rows_removed"],
            "cleaning_steps": [
                {"rule": s["rule"], "description": s["description"], "rows_removed": s["rows_removed"], "cells_changed": s["cells_changed"]}
                for s in analysis["cleaning_steps"]
            ],
        },
        "kpis": kpis["summary"],
        "breakdowns": breakdowns,
        "unavailable_kpis": kpis["unavailable"],
    }


def _fallback(analysis: dict, reason: str) -> dict:
    items = build_observations(analysis["kpis"], analysis["quality"])
    return {
        "source": "rule-based",
        "model": None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": None,
        "insights": items,
        "caveats": [],
        "notice": f"Rule-based observations, not AI-generated. {reason}",
    }


def generate_insights(analysis: dict, settings: Settings, client: anthropic.Anthropic | None = None) -> dict:
    if not settings.ai_configured and client is None:
        return _fallback(analysis, "No AI API key is configured on the server.")

    payload = build_ai_summary(analysis)
    try:
        client = client or anthropic.Anthropic(
            api_key=settings.ai_api_key, timeout=settings.ai_timeout_seconds, max_retries=1
        )
        response = client.messages.parse(
            model=settings.ai_model,
            max_tokens=4000,
            output_config={"effort": "medium"},
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": "Aggregated dataset summary (JSON):\n" + json.dumps(payload, indent=1),
                }
            ],
            output_format=AIInsightResponse,
        )
    except anthropic.AuthenticationError:
        return _fallback(analysis, "The AI service rejected the API key.")
    except anthropic.RateLimitError:
        return _fallback(analysis, "The AI service is rate-limited; try again later.")
    except anthropic.APIConnectionError:
        return _fallback(analysis, "The AI service could not be reached.")
    except anthropic.APIStatusError as exc:
        logger.warning("AI request failed with status %s", exc.status_code)
        return _fallback(analysis, f"The AI service returned an error ({exc.status_code}).")
    except Exception:  # validation errors and anything unexpected
        logger.exception("AI insight generation failed")
        return _fallback(analysis, "The AI response could not be used.")

    if response.stop_reason == "refusal" or response.parsed_output is None:
        return _fallback(analysis, "The AI service did not return usable insights.")

    parsed: AIInsightResponse = response.parsed_output
    return {
        "source": "ai",
        "model": response.model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": parsed.summary,
        "insights": [i.model_dump() for i in parsed.insights],
        "caveats": parsed.caveats,
        "notice": "AI-generated from the aggregated summary only. Check the evidence against the KPI tables before acting.",
    }
