"""Workflow automation: builds event payloads and delivers them to Make.com.

Events are only sent after an explicit user action, or by the single opt-in
rule AUTOMATION_TRIGGER_ON_REPORT. Payloads contain identifiers and summary
metrics only; raw dataset rows are never sent. A `report.generated` event
carries a short-lived signed link to the report PDF instead of the file
itself, and every event carries a signed link the scenario can call to report
whether its email (or other action) succeeded.
"""

from __future__ import annotations

import html
import json
import logging
import re
import uuid
from datetime import UTC, datetime

from app.config import Settings
from app.errors import AppError, NotFoundError, ValidationFailed
from app.integrations.make_webhook import DeliveryResult, MakeWebhookClient
from app.integrations.signed_links import REPORT_PDF, RUN_CONFIRMATION, LinkSigner
from app.reporting.document import format_metric, safe_download_name
from app.services.datasets import DatasetService
from app.storage.files import ReportFileStore
from app.storage.repositories import ActivityRepository, AutomationRepository, ReportRepository, utc_now

logger = logging.getLogger("flowforge.automation")

EVENT_TYPES = {
    "dataset.analysed": "Analysis summary for a dataset",
    "report.generated": "A report was generated, with a temporary link to its PDF",
    "automation.test": "Test event to check the connection. Contains no data.",
}
PAYLOAD_SCHEMA_VERSION = 2
# Gmail accepts attachments up to 25 MB; stay below it.
MAX_PDF_BYTES = 20 * 1024 * 1024
_SIGNATURE = re.compile(r"signature=[0-9a-f]{64}")


def redact_links(payload: dict, replacement: str = "redacted") -> dict:
    """Copy of a payload with link signatures removed, for storage and previews."""
    return json.loads(_SIGNATURE.sub(f"signature={replacement}", json.dumps(payload)))


def _timestamp(unix: int) -> str:
    return datetime.fromtimestamp(unix, UTC).isoformat(timespec="seconds")


def kpi_section(metrics: list[dict]) -> tuple[dict, list[dict], str]:
    """Flat KPI values, labelled KPIs with display text, and an HTML list for email bodies."""
    summary: dict = {}
    kpis: list[dict] = []
    for metric in metrics:
        item = {"key": metric["key"], "label": metric["label"], "format": metric["format"], "display": format_metric(metric)}
        if metric["format"] == "date_range":
            summary["date_range"] = {"start": metric["start"], "end": metric["end"]}
            item.update(value=None, start=metric["start"], end=metric["end"])
        else:
            summary[metric["key"]] = metric["value"]
            item["value"] = metric["value"]
        kpis.append(item)
    rows = "".join(f"<li><strong>{html.escape(item['label'])}:</strong> {html.escape(item['display'])}</li>" for item in kpis)
    return summary, kpis, f"<ul>{rows}</ul>" if rows else ""


class AutomationService:
    def __init__(
        self,
        settings: Settings,
        client: MakeWebhookClient,
        datasets: DatasetService,
        reports: ReportRepository,
        report_files: ReportFileStore,
        runs: AutomationRepository,
        activity: ActivityRepository,
        signer: LinkSigner,
    ):
        self.settings = settings
        self.client = client
        self.datasets = datasets
        self.reports = reports
        self.report_files = report_files
        self.runs = runs
        self.activity = activity
        self.signer = signer

    def status(self) -> dict:
        problem = self.client.configuration_problem
        link_problem = self.signer.configuration_problem
        return {
            "provider": "Make.com",
            "configured": problem is None,
            "configuration_problem": problem,
            "signing_enabled": bool(self.settings.make_webhook_secret),
            "trigger_on_report": self.settings.automation_trigger_on_report and problem is None,
            "timeout_seconds": self.settings.make_timeout_seconds,
            "event_types": [{"type": key, "description": value} for key, value in EVENT_TYPES.items()],
            "schema_version": PAYLOAD_SCHEMA_VERSION,
            "pdf_links": {
                "enabled": link_problem is None,
                "problem": link_problem,
                "ttl_minutes": self.signer.ttl_seconds // 60,
                "survive_restart": self.signer.persistent,
                "max_pdf_mb": MAX_PDF_BYTES // (1024 * 1024),
            },
        }

    # -- payload --------------------------------------------------------

    def _live_dataset_section(self, dataset_id: str) -> tuple[dict, list[dict]]:
        record = self.datasets.get_record(dataset_id)
        analysis = self.datasets.analysis(dataset_id)
        section = {
            "id": record["id"],
            "name": record["name"],
            "is_sample": bool(record["is_sample"]),
            "record_count": record["row_count"],
            "column_count": record["column_count"],
            "quality_score": record["quality_score"],
        }
        return section, analysis["metrics"]

    def _report_snapshot(self, report: dict) -> tuple[dict, list[dict]]:
        """Dataset details and KPIs exactly as they appear in the generated report."""
        path = self.report_files.path(report["id"], "json")
        if not path.is_file():
            raise NotFoundError("The stored report content is missing.", code="report_file_missing")
        document = json.loads(path.read_text(encoding="utf-8"))
        dataset = document["dataset"]
        section = {
            "id": dataset["id"],
            "name": dataset["name"],
            "is_sample": bool(dataset["is_sample"]),
            "record_count": dataset["record_count"],
            "column_count": dataset["column_count"],
            "quality_score": document["quality"]["score"],
        }
        return section, document.get("metrics", [])

    def _pdf_section(self, report: dict, run_id: str) -> dict:
        if "pdf" not in report["formats"]:
            return {"available": False, "reason": "This report has no PDF version."}
        path = self.report_files.path(report["id"], "pdf")
        if not path.is_file():
            return {"available": False, "reason": "The PDF file is no longer stored on the server."}
        size = path.stat().st_size
        if size > MAX_PDF_BYTES:
            return {"available": False, "reason": "The PDF is too large to send as an email attachment.", "size_bytes": size}
        link_problem = self.signer.configuration_problem
        if link_problem:
            return {"available": False, "reason": link_problem}
        url, expires = self.signer.link(REPORT_PDF, run_id, f"/api/automation/runs/{run_id}/report.pdf")
        return {
            "available": True,
            "filename": safe_download_name(report["title"], "pdf"),
            "content_type": "application/pdf",
            "size_bytes": size,
            "download_url": url,
            "expires_at": _timestamp(expires),
        }

    def build_payload(
        self,
        event_type: str,
        dataset_id: str | None = None,
        report_id: str | None = None,
        trigger: str = "manual",
        event_id: str | None = None,
    ) -> dict:
        """Build an event. Links in it are live; use `preview` to show one without them."""
        if event_type not in EVENT_TYPES:
            raise ValidationFailed(f"Unknown event type '{event_type}'.", code="invalid_event_type")
        event_id = event_id or uuid.uuid4().hex
        payload: dict = {
            "event": event_type,
            "event_id": event_id,
            "occurred_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "source": "flowforge-analytics",
            "schema_version": PAYLOAD_SCHEMA_VERSION,
            "trigger": trigger,
            "status": "completed",
            "dataset": None,
            "report": None,
            "summary": None,
            "kpis": [],
            "kpi_summary_html": "",
            "delivery": None,
        }
        if self.signer.configuration_problem is None:
            url, expires = self.signer.link(RUN_CONFIRMATION, event_id, f"/api/automation/runs/{event_id}/confirmation")
            payload["delivery"] = {"confirmation_url": url, "expires_at": _timestamp(expires)}

        if event_type == "automation.test":
            payload["message"] = "Test event from FlowForge Analytics. No dataset information is included."
            return payload

        if event_type == "report.generated":
            if not report_id:
                raise ValidationFailed("Choose a report to send.", code="report_required")
            report = self.reports.get(report_id)
            if report is None:
                raise NotFoundError("Report not found.", code="report_not_found")
            payload["dataset"], metrics = self._report_snapshot(report)
            payload["report"] = {
                "id": report["id"],
                "title": report["title"],
                "created_at": report["created_at"],
                "status": report["status"],
                "insight_mode": report["insight_mode"],
                "formats": report["formats"],
                "pdf": self._pdf_section(report, event_id),
            }
        else:
            if not dataset_id:
                raise ValidationFailed("Choose a dataset to send.", code="dataset_required")
            payload["dataset"], metrics = self._live_dataset_section(dataset_id)
        payload["summary"], payload["kpis"], payload["kpi_summary_html"] = kpi_section(metrics)
        return payload

    def preview(self, event_type: str, dataset_id: str | None = None, report_id: str | None = None) -> dict:
        return redact_links(self.build_payload(event_type, dataset_id, report_id), "added-when-sent")

    # -- delivery -------------------------------------------------------

    def trigger(
        self,
        event_type: str,
        dataset_id: str | None = None,
        report_id: str | None = None,
        trigger: str = "manual",
        resend: bool = False,
    ) -> dict:
        problem = self.client.configuration_problem
        if problem:
            raise AppError(f"Make.com is not configured: {problem}", code="automation_not_configured", status_code=409)
        if event_type == "report.generated" and report_id and not resend:
            previous = self.runs.latest_accepted_for_report(report_id)
            if previous:
                raise AppError(
                    "This report has already been sent to Make.com. Send it again only if the earlier delivery did not arrive.",
                    code="already_sent",
                    status_code=409,
                    details={"run_id": previous["id"], "sent_at": previous["created_at"]},
                )
        event_id = uuid.uuid4().hex
        payload = self.build_payload(event_type, dataset_id, report_id, trigger, event_id=event_id)
        # The run is stored before sending, because the scenario may fetch the PDF before the webhook call returns.
        self.runs.create(
            {
                "id": event_id,
                "event_type": event_type,
                "trigger": trigger,
                "dataset_id": (payload.get("dataset") or {}).get("id"),
                "report_id": (payload.get("report") or {}).get("id"),
                "status": "sending",
                "http_status": None,
                "message": "Sending to Make.com.",
                "duration_ms": None,
                "payload": redact_links(payload),
                "created_at": utc_now(),
            }
        )
        try:
            result = self.client.send(payload)
        except Exception:
            logger.exception("Unexpected error while sending a Make.com event")
            result = DeliveryResult("failed", "An unexpected error occurred while sending the event.")
        run = self.runs.finish(
            event_id,
            status=result.status,
            http_status=result.http_status,
            message=result.message,
            duration_ms=result.duration_ms,
            confirmation_status="pending" if result.status == "delivered" and payload["delivery"] else None,
        )
        logger.info("Make.com %s event %s: %s (HTTP %s)", event_type, event_id, result.status, result.http_status)
        self.activity.record(
            "automation." + result.status,
            f"Make.com {event_type} event: {result.message}",
            dataset_id=run["dataset_id"],
            report_id=run["report_id"],
        )
        return run

    def list_runs(self, limit: int = 50) -> list[dict]:
        return self.runs.list(limit)

    # -- signed links used by the Make.com scenario --------------------

    def _verify(self, purpose: str, run_id: str, expires: int, signature: str) -> dict:
        problem = self.signer.problem(purpose, run_id, expires, signature)
        if problem == "expired":
            raise AppError("This link has expired.", code="link_expired", status_code=410)
        if problem:
            raise AppError("This link is not valid.", code="link_invalid", status_code=403)
        run = self.runs.get(run_id)
        if run is None:
            raise NotFoundError("The automation event no longer exists.", code="run_not_found")
        return run

    def signed_pdf(self, run_id: str, expires: int, signature: str) -> tuple[bytes, str]:
        run = self._verify(REPORT_PDF, run_id, expires, signature)
        report = self.reports.get(run["report_id"]) if run["report_id"] else None
        if report is None or "pdf" not in report["formats"]:
            raise NotFoundError("The report PDF is no longer available.", code="report_file_missing")
        path = self.report_files.path(report["id"], "pdf")
        if not path.is_file():
            raise NotFoundError("The report PDF is no longer available.", code="report_file_missing")
        if path.stat().st_size > MAX_PDF_BYTES:
            raise AppError("The report PDF is too large to send.", code="file_too_large", status_code=413)
        content = path.read_bytes()
        if not content.startswith(b"%PDF-"):
            logger.error("Stored PDF for report %s is not a PDF file", report["id"])
            raise NotFoundError("The report PDF is no longer available.", code="report_file_missing")
        self.runs.mark_pdf_downloaded(run_id)
        return content, safe_download_name(report["title"], "pdf")

    def confirm(self, run_id: str, expires: int, signature: str, status: str, message: str | None) -> dict:
        self._verify(RUN_CONFIRMATION, run_id, expires, signature)
        run = self.runs.confirm(run_id, status, message)
        self.activity.record(
            "automation.confirmed" if status == "sent" else "automation.action_failed",
            "Make.com reported that its action succeeded." if status == "sent" else "Make.com reported that its action failed.",
            dataset_id=run["dataset_id"],
            report_id=run["report_id"],
        )
        return run
