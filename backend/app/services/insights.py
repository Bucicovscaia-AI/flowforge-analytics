"""Insight generation: rule-based by default, optionally extended by an AI provider.

Only an aggregated summary of the analysis is sent to an AI provider: metric
values, grouped totals, period totals and quality findings. Raw rows are never
included. Rule-based facts are always shown alongside AI output so that
measured figures can be checked against the AI's interpretation.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.engine.insights import FACT, generate_rule_based_insights
from app.integrations.ai.base import INSIGHT_CATEGORIES, INSIGHT_KINDS, AIProviderError, InsightProvider
from app.integrations.ai.factory import provider_label
from app.services.datasets import DatasetService

logger = logging.getLogger("flowforge.insights")

MAX_AI_INSIGHTS = 10
DATA_SENT_DESCRIPTION = [
    "Column names and inferred types",
    "Calculated metrics (totals, averages, counts)",
    "Grouped totals for up to 10 values per category, product, region and status column",
    "Totals per time period",
    "Correlation coefficients",
    "Data quality score and finding titles",
]


def build_ai_summary(analysis: dict, quality: dict) -> dict:
    """Reduce analysis output to aggregated figures suitable for an external provider."""
    breakdowns = {
        role: {
            "column": breakdown["column"],
            "measure": breakdown["measure"],
            "total_groups": breakdown["total_groups"],
            "top_groups": [
                {key: row[key] for key in ("group", "records", "revenue", "share") if row.get(key) is not None}
                for row in breakdown["rows"][:10]
            ],
        }
        for role, breakdown in analysis.get("breakdowns", {}).items()
    }
    series = analysis.get("time_series")
    return {
        "columns": [{"name": column["name"], "type": column["type"]} for column in analysis.get("columns", [])],
        "roles": {role: column for role, column in analysis.get("roles", {}).items() if column},
        "revenue_source": analysis.get("revenue_source"),
        "metrics": [
            {key: metric.get(key) for key in ("label", "value", "format", "start", "end") if metric.get(key) is not None}
            for metric in analysis.get("metrics", [])
        ],
        "breakdowns": breakdowns,
        "time_series": {
            "granularity": series["granularity"],
            "measure": series["aggregation"],
            "periods": [
                {"label": point["label"], "value": point["value"], "records": point["records"], "partial": point["partial"]}
                for point in series["points"][-36:]
            ],
        }
        if series
        else None,
        "period_comparison": analysis.get("period_comparison"),
        "trend": analysis.get("trend"),
        "correlations": analysis.get("correlations", []),
        "data_quality": {
            "score": quality.get("score"),
            "grade": quality.get("grade"),
            "findings": [
                {"severity": finding["severity"], "title": finding["title"], "affected_rows": finding["affected_rows"]}
                for finding in quality.get("findings", [])[:10]
            ],
        },
        "known_limitations": analysis.get("limitations", []),
    }


def _clean_text(value, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def normalise_ai_insights(payload: dict) -> tuple[list[dict], list[str]]:
    insights = []
    for index, item in enumerate((payload or {}).get("insights", [])[:MAX_AI_INSIGHTS]):
        if not isinstance(item, dict):
            continue
        title, statement = _clean_text(item.get("title"), 140), _clean_text(item.get("statement"), 600)
        if not title or not statement:
            continue
        evidence = [
            {"label": _clean_text(entry.get("label"), 80), "value": _clean_text(entry.get("value"), 80)}
            for entry in item.get("evidence", [])[:5]
            if isinstance(entry, dict) and entry.get("label")
        ]
        insights.append(
            {
                "id": f"ai-{index + 1}",
                "category": item.get("category") if item.get("category") in INSIGHT_CATEGORIES else "recommendation",
                "kind": item.get("kind") if item.get("kind") in INSIGHT_KINDS else "interpretation",
                "title": title,
                "statement": statement,
                "evidence": evidence,
                "caveat": _clean_text(item.get("caveat"), 300) or None,
                "source": "ai",
            }
        )
    limitations = [_clean_text(text, 300) for text in (payload or {}).get("limitations", [])[:5] if text]
    return insights, limitations


class InsightService:
    def __init__(self, datasets: DatasetService, provider: InsightProvider | None):
        self.datasets = datasets
        self.provider = provider

    @property
    def ai_available(self) -> bool:
        return self.provider is not None

    def generate(self, dataset_id: str, use_ai: bool = True) -> dict:
        analysis = self.datasets.analysis(dataset_id)
        quality = self.datasets.quality(dataset_id).to_dict()
        return self.generate_from(analysis, quality, use_ai)

    def generate_from(self, analysis: dict, quality: dict, use_ai: bool = True) -> dict:
        rule_based = [insight.to_dict() for insight in generate_rule_based_insights(analysis, quality)]
        notices: list[str] = []
        limitations = list(analysis.get("limitations", []))
        result = {
            "mode": "rule_based",
            "provider": None,
            "model": None,
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "insights": rule_based,
            "notices": notices,
            "limitations": limitations,
            "data_sent": [],
            "ai_error": None,
        }

        if use_ai and self.provider is not None:
            try:
                payload = self.provider.generate(build_ai_summary(analysis, quality))
                ai_insights, ai_limitations = normalise_ai_insights(payload)
                if not ai_insights:
                    raise AIProviderError("invalid_response", "The AI provider returned no usable insights.")
            except AIProviderError as error:
                logger.warning("AI insight generation failed: %s", error.reason)
                result["ai_error"] = error.reason
                notices.append(f"AI insights are unavailable: {error.message} Showing rule-based insights instead.")
            else:
                measured_facts = [insight for insight in rule_based if insight["kind"] == FACT]
                result.update(
                    mode="ai",
                    provider=provider_label(self.provider.name),
                    model=self.provider.model,
                    insights=measured_facts + ai_insights,
                    data_sent=DATA_SENT_DESCRIPTION,
                )
                limitations.extend(text for text in ai_limitations if text not in limitations)
                notices.append(
                    "AI-generated insights are interpretations of the calculated figures. Check them against the measured facts before acting on them."
                )
        elif use_ai:
            notices.append("No AI provider is configured, so these insights were produced by FlowForge's built-in rules.")

        if not result["insights"]:
            notices.append(
                "No insights could be produced: the dataset has no columns that support comparisons, trends or quality observations."
            )
        return result
