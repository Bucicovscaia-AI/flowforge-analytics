"""Client for delivering events to a Make.com custom webhook.

The webhook URL is a credential (anyone holding it can trigger the scenario),
so it is read from server configuration only and never returned to clients.
When MAKE_WEBHOOK_SECRET is set, each request carries an HMAC-SHA256 signature
of the body in the X-FlowForge-Signature header, which a Make scenario can use
to reject requests that did not come from this server.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

USER_AGENT = "FlowForge-Analytics/1.0"


@dataclass
class DeliveryResult:
    status: str  # "delivered", "failed" or "not_configured"
    message: str
    http_status: int | None = None
    duration_ms: int | None = None


def webhook_url_problem(url: str) -> str | None:
    """Return a description of what is wrong with a webhook URL, or None if it is acceptable."""
    if not url:
        return "MAKE_WEBHOOK_URL is not set."
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return "MAKE_WEBHOOK_URL must use HTTPS."
    if not parsed.hostname:
        return "MAKE_WEBHOOK_URL is not a valid URL."
    return None


def sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


class MakeWebhookClient:
    def __init__(self, url: str, secret: str = "", timeout_seconds: float = 10.0, transport: httpx.BaseTransport | None = None):
        self.url = url
        self.secret = secret
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    @property
    def configuration_problem(self) -> str | None:
        return webhook_url_problem(self.url)

    def send(self, payload: dict) -> DeliveryResult:
        problem = self.configuration_problem
        if problem:
            return DeliveryResult("not_configured", problem)
        body = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
        headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
        if self.secret:
            headers["X-FlowForge-Signature"] = sign(body, self.secret)
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout_seconds, transport=self.transport, follow_redirects=False) as client:
                response = client.post(self.url, content=body, headers=headers)
        except httpx.TimeoutException:
            return DeliveryResult(
                "failed",
                f"The webhook did not respond within {self.timeout_seconds:g} seconds.",
                duration_ms=self._elapsed(started),
            )
        except httpx.HTTPError:
            return DeliveryResult(
                "failed",
                "The webhook could not be reached. Check the URL and network connection.",
                duration_ms=self._elapsed(started),
            )
        elapsed = self._elapsed(started)
        if 200 <= response.status_code < 300:
            return DeliveryResult(
                "delivered", f"The webhook accepted the event (HTTP {response.status_code}).", response.status_code, elapsed
            )
        hint = {
            404: " The scenario's webhook may have been deleted.",
            410: " The webhook is no longer active.",
            429: " Make.com is rate limiting requests.",
        }.get(response.status_code, "")
        return DeliveryResult(
            "failed", f"The webhook rejected the event (HTTP {response.status_code}).{hint}", response.status_code, elapsed
        )

    @staticmethod
    def _elapsed(started: float) -> int:
        return int((time.perf_counter() - started) * 1000)
