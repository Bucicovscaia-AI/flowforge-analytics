"""Select the configured AI insight provider."""

from __future__ import annotations

import logging

from app.config import Settings
from app.integrations.ai.base import InsightProvider

logger = logging.getLogger("flowforge.ai")

SUPPORTED_PROVIDERS = {"anthropic": "Anthropic (Claude)"}


def provider_label(name: str) -> str:
    return SUPPORTED_PROVIDERS.get(name, name)


def build_insight_provider(settings: Settings) -> InsightProvider | None:
    if not settings.ai_configured:
        return None
    if settings.ai_provider == "anthropic":
        from app.integrations.ai.anthropic_provider import AnthropicInsightProvider

        return AnthropicInsightProvider(
            api_key=settings.ai_api_key,
            model=settings.ai_model,
            timeout_seconds=settings.ai_timeout_seconds,
            max_output_tokens=settings.ai_max_output_tokens,
        )
    logger.warning("AI_PROVIDER '%s' is not supported; AI insights are disabled.", settings.ai_provider)
    return None
