"""Short-lived signed links that let Make.com fetch a report PDF and confirm delivery.

A link carries an expiry time and an HMAC-SHA256 signature over its purpose,
the resource identifier and that expiry, so it works for one resource and one
purpose only, cannot be extended, and needs no login. The key comes from
REPORT_LINK_SECRET. Without it a random key is generated at start-up, which
means links stop working when the server restarts; on hosts with temporary
storage the report files are gone after a restart anyway.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections.abc import Callable
from urllib.parse import urlencode, urlparse

REPORT_PDF = "report-pdf"
RUN_CONFIRMATION = "run-confirmation"


def base_url_problem(url: str) -> str | None:
    """Return why links cannot be built from this base URL, or None if they can."""
    if not url:
        return "PUBLIC_BASE_URL is not set, so FlowForge cannot build a link Make.com can reach."
    parsed = urlparse(url)
    if not parsed.hostname:
        return "PUBLIC_BASE_URL is not a valid URL."
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        return "PUBLIC_BASE_URL must use HTTPS."
    return None


class LinkSigner:
    def __init__(self, base_url: str, secret: str = "", ttl_seconds: int = 3600, clock: Callable[[], float] = time.time):
        self.base_url = base_url.rstrip("/")
        self.persistent = bool(secret)
        self._key = secret.encode("utf-8") if secret else secrets.token_bytes(32)
        self.ttl_seconds = ttl_seconds
        self.clock = clock

    @property
    def configuration_problem(self) -> str | None:
        return base_url_problem(self.base_url)

    def _signature(self, purpose: str, resource_id: str, expires: int) -> str:
        message = f"{purpose}:{resource_id}:{expires}".encode()
        return hmac.new(self._key, message, hashlib.sha256).hexdigest()

    def link(self, purpose: str, resource_id: str, path: str) -> tuple[str, int]:
        """Return an absolute signed URL for `path` and its expiry as a Unix timestamp."""
        expires = int(self.clock()) + self.ttl_seconds
        query = urlencode({"expires": expires, "signature": self._signature(purpose, resource_id, expires)})
        return f"{self.base_url}{path}?{query}", expires

    def problem(self, purpose: str, resource_id: str, expires: int, signature: str) -> str | None:
        """Return "invalid" or "expired" if the link must be refused, or None if it is valid."""
        if not hmac.compare_digest(self._signature(purpose, resource_id, expires), signature or ""):
            return "invalid"
        if expires < self.clock():
            return "expired"
        return None
