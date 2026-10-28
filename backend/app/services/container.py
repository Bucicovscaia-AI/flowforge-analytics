"""Construct the application's services from settings."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.integrations.ai.base import InsightProvider
from app.integrations.ai.factory import build_insight_provider
from app.integrations.make_webhook import MakeWebhookClient
from app.integrations.signed_links import LinkSigner
from app.services.automation import AutomationService
from app.services.datasets import DatasetService
from app.services.insights import InsightService
from app.services.reports import ReportService
from app.storage.database import Database
from app.storage.files import DatasetFileStore, ReportFileStore
from app.storage.repositories import ActivityRepository, AutomationRepository, DatasetRepository, ReportRepository


@dataclass
class Services:
    settings: Settings
    datasets: DatasetService
    insights: InsightService
    reports: ReportService
    automation: AutomationService
    activity: ActivityRepository


def build_services(
    settings: Settings, *, insight_provider: InsightProvider | None = None, webhook_client: MakeWebhookClient | None = None
) -> Services:
    database = Database(settings.database_path)
    activity = ActivityRepository(database)
    report_repository = ReportRepository(database)
    datasets = DatasetService(settings, DatasetRepository(database), DatasetFileStore(settings.datasets_dir), activity)
    provider = insight_provider if insight_provider is not None else build_insight_provider(settings)
    insights = InsightService(datasets, provider)
    client = webhook_client or MakeWebhookClient(
        settings.make_webhook_url, settings.make_webhook_secret, settings.make_timeout_seconds
    )
    report_files = ReportFileStore(settings.reports_dir)
    signer = LinkSigner(settings.public_base_url, settings.report_link_secret, settings.report_link_ttl_minutes * 60)
    automation = AutomationService(
        settings, client, datasets, report_repository, report_files, AutomationRepository(database), activity, signer
    )
    reports = ReportService(settings, datasets, insights, automation, report_repository, report_files, activity)
    return Services(settings, datasets, insights, reports, automation, activity)
