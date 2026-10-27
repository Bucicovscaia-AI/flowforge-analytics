"""Workflow automation: builds event payloads and delivers them to Make.com.

Events are only sent after an explicit user action, or by the single opt-in
rule AUTOMATION_TRIGGER_ON_REPORT. Payloads contain identifiers and summary
metrics only; raw dataset rows are never sent.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.config import Settings
from app.errors import AppError, NotFoundError, ValidationFailed
from app.integrations.make_webhook import MakeWebhookClient
from app.services.datasets import DatasetService
from app.storage.repositories import ActivityRepository, AutomationRepository, ReportRepository, utc_now

EVENT_TYPES = {
    "dataset.analysed": "Analysis summary for a dataset",
    "report.generated": "A report was generated",
    "automation.test": "Test event to check the connection",
}
PAYLOAD_SCHEMA_VERSION = 1


class AutomationService:
    def __init__(
        self,
        settings: Settings,
        client: MakeWebhookClient,
        datasets: DatasetService,
        reports: ReportRepository,
        runs: AutomationRepository,
        activity: ActivityRepository,
    ):
        self.settings = settings
        self.client = client
        self.datasets = datasets
        self.reports = reports
        self.runs = runs
        self.activity = activity

    def status(self) -> dict:
        problem = self.client.configuration_problem
        return {
            "provider": "Make.com",
            "configured": problem is None,
            "configuration_problem": problem,
            "signing_enabled": bool(self.settings.make_webhook_secret),
            "trigger_on_report": self.settings.automation_trigger_on_report and problem is None,
            "timeout_seconds": self.settings.make_timeout_seconds,
            "event_types": [{"type": key, "description": value} for key, value in EVENT_TYPES.items()],
        }

    def _dataset_section(self, dataset_id: str) -> tuple[dict, dict]:
        record = self.datasets.get_record(dataset_id)
        analysis = self.datasets.analysis(dataset_id)
        metrics = {}
        for metric in analysis["metrics"]:
            if metric["format"] == "date_range":
                metrics["date_range"] = {"start": metric["start"], "end": metric["end"]}
            else:
                metrics[metric["key"]] = metric["value"]
        section = {
            "id": record["id"],
            "name": record["name"],
            "is_sample": bool(record["is_sample"]),
            "record_count": record["row_count"],
            "column_count": record["column_count"],
            "quality_score": record["quality_score"],
        }
        return section, metrics

    def build_payload(
        self, event_type: str, dataset_id: str | None = None, report_id: str | None = None, trigger: str = "manual"
    ) -> dict:
        if event_type not in EVENT_TYPES:
            raise ValidationFailed(f"Unknown event type '{event_type}'.", code="invalid_event_type")
        payload: dict = {
            "event": event_type,
            "event_id": uuid.uuid4().hex,
            "occurred_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "source": "flowforge-analytics",
            "schema_version": PAYLOAD_SCHEMA_VERSION,
            "trigger": trigger,
            "status": "completed",
            "dataset": None,
            "report": None,
            "summary": None,
        }
        if event_type == "automation.test":
            payload["message"] = "Test event from FlowForge Analytics. No dataset information is included."
            return payload

        report = None
        if event_type == "report.generated":
            if not report_id:
                raise ValidationFailed("Choose a report to send.", code="report_required")
            report = self.reports.get(report_id)
            if report is None:
                raise NotFoundError("Report not found.", code="report_not_found")
            dataset_id = report["dataset_id"]
        if not dataset_id:
            raise ValidationFailed("Choose a dataset to send.", code="dataset_required")
        payload["dataset"], payload["summary"] = self._dataset_section(dataset_id)
        if report:
            payload["report"] = {
                "id": report["id"],
                "title": report["title"],
                "created_at": report["created_at"],
                "status": report["status"],
                "insight_mode": report["insight_mode"],
                "formats": report["formats"],
            }
            if self.settings.public_base_url:
                payload["report"]["download_url"] = (
                    f"{self.settings.public_base_url}/api/reports/{report['id']}/download?format=html"
                )
        return payload

    def trigger(
        self, event_type: str, dataset_id: str | None = None, report_id: str | None = None, trigger: str = "manual"
    ) -> dict:
        problem = self.client.configuration_problem
        if problem:
            raise AppError(f"Make.com is not configured: {problem}", code="automation_not_configured", status_code=409)
        payload = self.build_payload(event_type, dataset_id, report_id, trigger)
        result = self.client.send(payload)
        run = self.runs.create(
            {
                "id": uuid.uuid4().hex,
                "event_type": event_type,
                "trigger": trigger,
                "dataset_id": (payload.get("dataset") or {}).get("id"),
                "report_id": (payload.get("report") or {}).get("id"),
                "status": result.status,
                "http_status": result.http_status,
                "message": result.message,
                "duration_ms": result.duration_ms,
                "payload": payload,
                "created_at": utc_now(),
            }
        )
        self.activity.record(
            "automation." + result.status,
            f"Make.com {event_type} event: {result.message}",
            dataset_id=run["dataset_id"],
            report_id=run["report_id"],
        )
        return run

    def list_runs(self, limit: int = 50) -> list[dict]:
        return self.runs.list(limit)
