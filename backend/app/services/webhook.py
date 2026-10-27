"""Make.com webhook integration.

When a report is generated (or the user presses "Send test event"), the
backend POSTs a JSON summary to a Make.com custom webhook. A Make scenario can
then, for example, post the KPIs to Slack, add a row to Google Sheets or email
the team. See docs/make-integration.md for the scenario set-up.

Security:
* The webhook URL is a secret (anyone holding it can trigger the scenario),
  so it is read from the environment, never sent to the browser and never
  logged. The API only reports whether it is configured and its host name.
* Only https URLs are accepted.
* If MAKE_WEBHOOK_API_KEY is set it is sent in the ``x-make-apikey`` header,
  which Make checks when the webhook has API-key authentication turned on.
* No raw rows are sent: only aggregated KPIs and report metadata.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx2

from app.config import APP_VERSION, Settings

logger = logging.getLogger(__name__)


class WebhookError(Exception):
    pass


def describe_target(settings: Settings) -> str | None:
    """Host only, e.g. 'hook.eu1.make.com'. The path holds the secret."""
    if not settings.webhook_configured:
        return None
    return urlparse(settings.make_webhook_url).hostname


def build_report_payload(report: dict, analysis: dict, insights: dict | None) -> dict:
    summary = analysis["kpis"]["summary"]
    breakdowns = analysis["kpis"]["breakdowns"]
    top = lambda key: (breakdowns.get(key) or [None])[0]  # noqa: E731
    items = (insights or {}).get("insights") or analysis["observations"]
    return {
        "event": "report.generated",
        "report": {
            "id": report["id"],
            "title": report["title"],
            "created_at": report["created_at"],
            "download_path": f"/api/reports/{report['id']}/download",
        },
        "dataset": {
            "file_name": analysis["dataset"]["file_name"],
            "synthetic": analysis["dataset"]["synthetic"],
            "rows_received": analysis["quality"]["rows_received"],
            "rows_analysed": analysis["quality"]["rows_analysed"],
            "data_quality_score": analysis["quality"]["quality_score"],
        },
        "kpis": {
            "currency": summary["currency"],
            "total_revenue": summary["total_revenue"],
            "order_count": summary["order_count"],
            "units_sold": summary["units_sold"],
            "average_order_value": summary["average_order_value"],
            "date_from": summary.get("date_from"),
            "date_to": summary.get("date_to"),
        },
        "top_category": top("revenue_by_category"),
        "top_region": top("revenue_by_region"),
        "insight_source": (insights or {}).get("source", "rule-based"),
        "highlights": [i["title"] for i in items[:5]],
    }


def send_event(payload: dict, settings: Settings, transport: httpx2.BaseTransport | None = None) -> dict:
    """POST one event. Retries once on a timeout or 5xx response."""
    if not settings.webhook_configured:
        raise WebhookError("The Make.com webhook is not configured (set MAKE_WEBHOOK_URL on the server).")
    url = settings.make_webhook_url
    if urlparse(url).scheme != "https":
        raise WebhookError("MAKE_WEBHOOK_URL must be an https URL.")

    body = {
        "event_id": str(uuid.uuid4()),
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "source": "flowforge-analytics",
        "app_version": APP_VERSION,
        **payload,
    }
    headers = {"Content-Type": "application/json", "User-Agent": f"FlowForge/{APP_VERSION}"}
    if settings.make_webhook_api_key:
        headers["x-make-apikey"] = settings.make_webhook_api_key

    last_error = ""
    with httpx2.Client(timeout=settings.make_timeout_seconds, transport=transport) as client:
        for attempt in (1, 2):
            try:
                response = client.post(url, json=body, headers=headers)
            except httpx2.TimeoutException:
                last_error = "Make.com did not respond in time."
            except httpx2.HTTPError:
                last_error = "Make.com could not be reached."
            else:
                if response.is_success:
                    return {
                        "delivered": True,
                        "status_code": response.status_code,
                        "event_id": body["event_id"],
                        "response": response.text[:200],
                        "attempts": attempt,
                    }
                if response.status_code < 500:
                    # 4xx will not succeed on retry: wrong URL, disabled
                    # scenario, or a bad API key.
                    raise WebhookError(f"Make.com rejected the event (HTTP {response.status_code}). Check the webhook and API key.")
                last_error = f"Make.com returned HTTP {response.status_code}."
            if attempt == 1:
                time.sleep(0.5)
    logger.warning("Webhook delivery failed: %s", last_error)
    raise WebhookError(last_error)
