"""Insight provider backed by the Anthropic Messages API."""

from __future__ import annotations

import json
import logging

from app.integrations.ai.base import INSIGHT_SCHEMA, SYSTEM_PROMPT, AIProviderError

logger = logging.getLogger("flowforge.ai")


class AnthropicInsightProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str, timeout_seconds: float, max_output_tokens: int, client=None):
        self.model = model
        self.max_output_tokens = max_output_tokens
        if client is None:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key, timeout=timeout_seconds, max_retries=1)
        self._client = client

    def generate(self, summary: dict) -> dict:
        import anthropic

        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_output_tokens,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": "Analysis summary (JSON):\n" + json.dumps(summary, ensure_ascii=False, default=str),
                    }
                ],
                output_config={"format": {"type": "json_schema", "schema": INSIGHT_SCHEMA}},
            )
        except anthropic.AuthenticationError as error:
            raise AIProviderError("authentication", "The AI provider rejected the configured API key.") from error
        except anthropic.PermissionDeniedError as error:
            raise AIProviderError("authentication", "The configured API key does not have access to this model.") from error
        except anthropic.NotFoundError as error:
            raise AIProviderError("configuration", f"The AI model '{self.model}' was not found. Check AI_MODEL.") from error
        except anthropic.RateLimitError as error:
            raise AIProviderError("rate_limited", "The AI provider's rate limit was reached. Try again in a minute.") from error
        except anthropic.APITimeoutError as error:
            raise AIProviderError("timeout", "The AI provider did not respond in time.") from error
        except anthropic.APIConnectionError as error:
            raise AIProviderError("unavailable", "The AI provider could not be reached.") from error
        except anthropic.APIStatusError as error:
            logger.warning("AI provider returned HTTP %s", error.status_code)
            raise AIProviderError("unavailable", f"The AI provider returned an error (HTTP {error.status_code}).") from error

        if getattr(response, "stop_reason", None) == "refusal":
            raise AIProviderError("refused", "The AI provider declined to generate insights for this summary.")
        if getattr(response, "stop_reason", None) == "max_tokens":
            raise AIProviderError("invalid_response", "The AI response was cut off before it was complete.")
        text = next((block.text for block in response.content if getattr(block, "type", None) == "text"), None)
        if not text:
            raise AIProviderError("invalid_response", "The AI provider returned no text.")
        try:
            return json.loads(text)
        except json.JSONDecodeError as error:
            raise AIProviderError("invalid_response", "The AI provider returned a response that was not valid JSON.") from error
