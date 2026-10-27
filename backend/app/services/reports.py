"""Report generation, storage and retrieval."""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import UTC, datetime

from app.config import Settings
from app.errors import NotFoundError
from app.reporting.csv_export import report_to_csv_bytes
from app.reporting.document import build_report_document
from app.reporting.html_report import render_html
from app.reporting.pdf_report import render_pdf
from app.services.automation import AutomationService
from app.services.datasets import DatasetService, clean_display_name
from app.services.insights import InsightService
from app.storage.files import ReportFileStore
from app.storage.repositories import ActivityRepository, ReportRepository

logger = logging.getLogger("flowforge.reports")

FORMATS = {
    "html": ("text/html; charset=utf-8", "html"),
    "pdf": ("application/pdf", "pdf"),
    "csv": ("text/csv; charset=utf-8", "csv"),
    "json": ("application/json", "json"),
}


def safe_download_name(title: str, extension: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-").lower()[:60] or "report"
    return f"{slug}.{extension}"


class ReportService:
    def __init__(
        self,
        settings: Settings,
        datasets: DatasetService,
        insights: InsightService,
        automation: AutomationService,
        repository: ReportRepository,
        files: ReportFileStore,
        activity: ActivityRepository,
    ):
        self.settings = settings
        self.datasets = datasets
        self.insights = insights
        self.automation = automation
        self.repository = repository
        self.files = files
        self.activity = activity

    def generate(self, dataset_id: str, title: str | None = None, use_ai: bool = True) -> dict:
        record = self.datasets.get_record(dataset_id)
        analysis = self.datasets.analysis(dataset_id)
        quality = self.datasets.quality(dataset_id).to_dict()
        insights = self.insights.generate_from(analysis, quality, use_ai)
        report_id = uuid.uuid4().hex
        title = (
            clean_display_name(title)
            if title and title.strip()
            else (f"{record['name']} analysis – {datetime.now(UTC).strftime('%d %b %Y')}")
        )
        document = build_report_document(
            report_id=report_id,
            title=title,
            dataset=record,
            operations=self.datasets.repository.operations(dataset_id),
            analysis=analysis,
            quality=quality,
            insights=insights,
        )

        formats, problems = [], []
        renderers = {
            "json": lambda: json.dumps(document, indent=2, default=str).encode("utf-8"),
            "html": lambda: render_html(document).encode("utf-8"),
            "csv": lambda: report_to_csv_bytes(document),
            "pdf": lambda: render_pdf(document),
        }
        for extension, render in renderers.items():
            try:
                self.files.write(report_id, extension, render())
                formats.append(extension)
            except Exception:
                logger.exception("Rendering %s report failed", extension)
                problems.append(extension.upper())
        status = "completed" if not problems else ("partial" if formats else "failed")
        report = self.repository.create(
            {
                "id": report_id,
                "title": title,
                "dataset_id": dataset_id,
                "dataset_name": record["name"],
                "created_at": document["generated_at"],
                "status": status,
                "insight_mode": insights["mode"],
                "record_count": record["row_count"],
                "formats": formats,
                "error": f"Could not produce: {', '.join(problems)}." if problems else None,
            }
        )
        self.activity.record("report.generated", f"Report generated: {title}", dataset_id=dataset_id, report_id=report_id)

        automation_run = None
        if self.settings.automation_trigger_on_report and self.automation.status()["configured"] and status != "failed":
            automation_run = self.automation.trigger("report.generated", report_id=report_id, trigger="rule")
        return {**report, "automation_run": automation_run}

    def get(self, report_id: str) -> dict:
        report = self.repository.get(report_id)
        if report is None:
            raise NotFoundError("Report not found. It may have been deleted.", code="report_not_found")
        return report

    def document(self, report_id: str) -> dict:
        self.get(report_id)
        path = self.files.path(report_id, "json")
        if not path.is_file():
            raise NotFoundError("The stored report content is missing.", code="report_file_missing")
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self, dataset_id: str | None = None, limit: int = 100) -> list[dict]:
        return self.repository.list(dataset_id, limit)

    def file(self, report_id: str, fmt: str) -> tuple[bytes, str, str]:
        report = self.get(report_id)
        if fmt not in FORMATS or fmt not in report["formats"]:
            raise NotFoundError(f"This report is not available as {fmt.upper()}.", code="format_unavailable")
        path = self.files.path(report_id, FORMATS[fmt][1])
        if not path.is_file():
            raise NotFoundError("The stored report file is missing.", code="report_file_missing")
        return path.read_bytes(), FORMATS[fmt][0], safe_download_name(report["title"], FORMATS[fmt][1])

    def delete(self, report_id: str) -> None:
        report = self.get(report_id)
        self.files.delete(report_id)
        self.repository.delete(report_id)
        self.activity.record("report.deleted", f"Report deleted: {report['title']}")
