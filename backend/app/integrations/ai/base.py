"""Provider-independent interface for AI-generated insights.

A provider receives an aggregated analysis summary (never raw rows) and returns
a list of insight dictionaries. Adding a provider means implementing
`InsightProvider` and registering it in `factory.py`.
"""

from __future__ import annotations

from typing import Protocol

INSIGHT_CATEGORIES = ["trend", "performance", "composition", "relationship", "data_quality", "recommendation", "question"]
INSIGHT_KINDS = ["fact", "interpretation", "suggestion"]

INSIGHT_SCHEMA = {
    "type": "object",
    "properties": {
        "insights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": INSIGHT_CATEGORIES},
                    "kind": {"type": "string", "enum": INSIGHT_KINDS},
                    "title": {"type": "string"},
                    "statement": {"type": "string"},
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"label": {"type": "string"}, "value": {"type": "string"}},
                            "required": ["label", "value"],
                            "additionalProperties": False,
                        },
                    },
                    "caveat": {"type": "string"},
                },
                "required": ["category", "kind", "title", "statement", "evidence", "caveat"],
                "additionalProperties": False,
            },
        },
        "limitations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["insights", "limitations"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are a careful business data analyst writing insights for a dashboard.

You receive a JSON summary of an analysis that has already been calculated. Write 4 to 8 insights that help a non-specialist understand the results.

Rules:
- Use only figures that appear in the summary. Never invent, estimate or extrapolate numbers.
- Label each insight's kind: "fact" for something directly measured in the summary, "interpretation" for your reading of what the figures suggest, "suggestion" for a follow-up analysis or question.
- Do not claim that one thing causes another. Correlations and co-occurring changes are not evidence of cause.
- Do not give financial, legal or investment advice. Recommendations must be limited to further analysis or data checks.
- Mention data quality problems when they could affect conclusions.
- In evidence, quote the exact figures from the summary that support the insight.
- Use the caveat field for limitations of the insight; use an empty string if there is none.
- Write in plain British English. Keep each statement under 60 words."""


class AIProviderError(Exception):
    """Raised when the provider cannot return usable insights."""

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


class InsightProvider(Protocol):
    name: str
    model: str

    def generate(self, summary: dict) -> dict:
        """Return {"insights": [...], "limitations": [...]} matching INSIGHT_SCHEMA."""
        ...
