"""Dataset lifecycle: import, inspection, cleaning, analysis and deletion."""

from __future__ import annotations

import re
import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import PurePath

import pandas as pd

from app.config import Settings
from app.engine import analytics, cleaning
from app.engine.loading import CSVValidationError, parse_csv_bytes
from app.engine.profiling import (
    NUMERIC,
    ROLE_DEFINITIONS,
    DatasetProfile,
    profile_frame,
    resolve_roles,
    role_candidates,
    typed_frame,
)
from app.engine.quality import QualityContext, QualityReport, assess_quality
from app.errors import AppError, NotFoundError, ValidationFailed
from app.reporting.csv_export import frame_to_csv_bytes
from app.storage.files import DatasetFileStore
from app.storage.repositories import ActivityRepository, DatasetRepository, utc_now

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def display_name_from_filename(filename: str | None) -> str:
    """Derive a readable dataset name from an untrusted filename (display only, never a path)."""
    base = PurePath((filename or "").replace("\\", "/")).name
    stem = base.rsplit(".", 1)[0] if "." in base else base
    stem = _CONTROL_CHARS.sub("", stem).replace("_", " ").strip()
    stem = re.sub(r"\s+", " ", stem)
    return stem[:120] or "Untitled dataset"


def clean_display_name(name: str) -> str:
    cleaned = re.sub(r"\s+", " ", _CONTROL_CHARS.sub("", name)).strip()
    if not cleaned:
        raise ValidationFailed("The dataset name cannot be empty.")
    return cleaned[:120]


@dataclass
class Workspace:
    """A loaded dataset with its inferred profile and resolved column roles."""

    frame: pd.DataFrame
    profile: DatasetProfile
    roles: dict[str, str | None]
    typed: pd.DataFrame

    @property
    def analysis_context(self) -> analytics.AnalysisContext:
        return analytics.AnalysisContext(self.typed, self.profile, self.roles)

    @property
    def quality_context(self) -> QualityContext:
        return QualityContext(self.frame, self.typed, self.profile, self.roles)


def build_workspace(frame: pd.DataFrame, mapping: dict | None) -> Workspace:
    profile = profile_frame(frame)
    roles = resolve_roles(profile, mapping)
    return Workspace(frame=frame, profile=profile, roles=roles, typed=typed_frame(frame, profile))


class DatasetService:
    CACHE_SIZE = 6

    def __init__(self, settings: Settings, repository: DatasetRepository, files: DatasetFileStore, activity: ActivityRepository):
        self.settings = settings
        self.repository = repository
        self.files = files
        self.activity = activity
        self._cache: OrderedDict[str, tuple[float, str, Workspace]] = OrderedDict()
        self._lock = threading.Lock()

    # -- lookup ---------------------------------------------------------

    def get_record(self, dataset_id: str) -> dict:
        record = self.repository.get(dataset_id)
        if record is None:
            raise NotFoundError("Dataset not found. It may have been deleted.", code="dataset_not_found")
        return record

    def list_records(self) -> list[dict]:
        return self.repository.list()

    def workspace(self, dataset_id: str) -> Workspace:
        record = self.get_record(dataset_id)
        path = self.files.working_path(dataset_id)
        if not path.is_file():
            raise AppError(
                "The stored data for this dataset is missing. Delete it and import the file again.",
                code="dataset_file_missing",
                status_code=409,
            )
        stamp = path.stat().st_mtime_ns
        mapping_key = repr(sorted(record["column_mapping"].items()))
        with self._lock:
            cached = self._cache.get(dataset_id)
            if cached and cached[0] == stamp and cached[1] == mapping_key:
                self._cache.move_to_end(dataset_id)
                return cached[2]
        workspace = build_workspace(self.files.read_working(dataset_id), record["column_mapping"])
        with self._lock:
            self._cache[dataset_id] = (stamp, mapping_key, workspace)
            self._cache.move_to_end(dataset_id)
            while len(self._cache) > self.CACHE_SIZE:
                self._cache.popitem(last=False)
        return workspace

    def _invalidate(self, dataset_id: str) -> None:
        with self._lock:
            self._cache.pop(dataset_id, None)

    # -- import ---------------------------------------------------------

    def import_csv(self, data: bytes, *, filename: str | None, name: str | None = None, is_sample: bool = False) -> dict:
        try:
            parsed = parse_csv_bytes(data, max_rows=self.settings.max_rows, max_columns=self.settings.max_columns)
        except CSVValidationError as error:
            raise ValidationFailed(error.message, code=error.code) from error

        dataset_id = uuid.uuid4().hex
        display_name = clean_display_name(name) if name and name.strip() else display_name_from_filename(filename)
        workspace = build_workspace(parsed.frame, {})
        quality = assess_quality(workspace.quality_context)
        size = self.files.write_initial(dataset_id, parsed.frame)
        now = utc_now()
        record = self.repository.create(
            {
                "id": dataset_id,
                "name": display_name,
                "source_filename": display_name_from_filename(filename) if filename else None,
                "is_sample": int(is_sample),
                "status": "ready",
                "created_at": now,
                "updated_at": now,
                "original_row_count": len(parsed.frame),
                "row_count": len(parsed.frame),
                "column_count": parsed.frame.shape[1],
                "size_bytes": size,
                "encoding": parsed.encoding,
                "delimiter": parsed.delimiter,
                "quality_score": quality.score,
                "quality_grade": quality.grade,
                "column_mapping": {},
                "warnings": parsed.warnings,
            }
        )
        label = "Sample dataset loaded" if is_sample else "Dataset imported"
        self.activity.record("dataset.imported", f"{label}: {display_name} ({len(parsed.frame):,} rows)", dataset_id=dataset_id)
        return record

    def import_sample(self) -> dict:
        path = self.settings.sample_data_path
        if not path.is_file():
            raise AppError("The sample dataset file is not available on the server.", code="sample_missing", status_code=500)
        return self.import_csv(path.read_bytes(), filename=path.name, name="Retail orders (synthetic sample)", is_sample=True)

    # -- metadata -------------------------------------------------------

    def detail(self, dataset_id: str) -> dict:
        record = self.get_record(dataset_id)
        workspace = self.workspace(dataset_id)
        return {
            **record,
            "columns": [column.to_dict() for column in workspace.profile.columns],
            "roles": workspace.roles,
            "role_options": {
                role: {"label": definition["label"], "candidates": role_candidates(workspace.profile, role)}
                for role, definition in ROLE_DEFINITIONS.items()
            },
            "operations": self.repository.operations(dataset_id),
        }

    def rename(self, dataset_id: str, name: str) -> dict:
        self.get_record(dataset_id)
        return self.repository.update(dataset_id, name=clean_display_name(name))

    def update_mapping(self, dataset_id: str, mapping: dict[str, str | None]) -> dict:
        record = self.get_record(dataset_id)
        workspace = self.workspace(dataset_id)
        stored = dict(record["column_mapping"])
        for role, column in mapping.items():
            if role not in ROLE_DEFINITIONS:
                raise ValidationFailed(f"Unknown role '{role}'.")
            if column is None:
                stored.pop(role, None)
            elif column == "":
                stored[role] = ""
            elif column not in role_candidates(workspace.profile, role):
                raise ValidationFailed(f"Column '{column}' cannot be used as {ROLE_DEFINITIONS[role]['label'].lower()}.")
            else:
                stored[role] = column
        self.repository.update(dataset_id, column_mapping=stored)
        self._invalidate(dataset_id)
        self._refresh_quality(dataset_id)
        return self.detail(dataset_id)

    def delete(self, dataset_id: str) -> None:
        record = self.get_record(dataset_id)
        self.files.delete(dataset_id)
        self.repository.delete(dataset_id)
        self._invalidate(dataset_id)
        self.activity.record("dataset.deleted", f"Dataset deleted: {record['name']}")

    def preview(self, dataset_id: str, offset: int, limit: int) -> dict:
        workspace = self.workspace(dataset_id)
        window = workspace.frame.iloc[offset : offset + limit]
        rows = [[None if pd.isna(value) else str(value) for value in row] for row in window.itertuples(index=False, name=None)]
        return {
            "columns": [{"name": column.name, "type": column.inferred_type} for column in workspace.profile.columns],
            "rows": rows,
            "offset": offset,
            "limit": limit,
            "total_rows": len(workspace.frame),
        }

    # -- quality and cleaning -----------------------------------------

    def quality(self, dataset_id: str) -> QualityReport:
        return assess_quality(self.workspace(dataset_id).quality_context)

    def _refresh_quality(self, dataset_id: str) -> QualityReport:
        report = self.quality(dataset_id)
        workspace = self.workspace(dataset_id)
        self.repository.update(
            dataset_id,
            quality_score=report.score,
            quality_grade=report.grade,
            row_count=len(workspace.frame),
            column_count=workspace.frame.shape[1],
        )
        return report

    def _run_operation(self, dataset_id: str, operation: str, params: dict):
        workspace = self.workspace(dataset_id)
        try:
            return workspace, *cleaning.apply_operation(workspace.frame, operation, params)
        except cleaning.CleaningError as error:
            raise ValidationFailed(str(error), code="invalid_operation") from error

    def preview_operation(self, dataset_id: str, operation: str, params: dict) -> dict:
        record = self.get_record(dataset_id)
        _, result_frame, result = self._run_operation(dataset_id, operation, params)
        after = assess_quality(build_workspace(result_frame, record["column_mapping"]).quality_context)
        return {**result.to_dict(), "quality_before": record["quality_score"], "quality_after": after.score, "applied": False}

    def apply_operation(self, dataset_id: str, operation: str, params: dict) -> dict:
        record = self.get_record(dataset_id)
        _, result_frame, result = self._run_operation(dataset_id, operation, params)
        if not result.changed:
            return {
                **result.to_dict(),
                "quality_before": record["quality_score"],
                "quality_after": record["quality_score"],
                "applied": False,
                "message": "No changes were needed, so the dataset was not modified.",
            }
        self.files.write_working(dataset_id, result_frame)
        self._invalidate(dataset_id)
        report = self._refresh_quality(dataset_id)
        self.repository.add_operation(
            dataset_id,
            operation,
            result.params,
            result.summary,
            result.rows_before,
            result.rows_after,
            record["quality_score"],
            report.score,
        )
        self.activity.record("dataset.cleaned", f"{record['name']}: {result.summary}", dataset_id=dataset_id)
        return {**result.to_dict(), "quality_before": record["quality_score"], "quality_after": report.score, "applied": True}

    def reset(self, dataset_id: str) -> dict:
        record = self.get_record(dataset_id)
        self.files.reset_working(dataset_id)
        self._invalidate(dataset_id)
        report = self._refresh_quality(dataset_id)
        self.repository.add_operation(
            dataset_id,
            "reset",
            {},
            "Restored the original imported data.",
            record["row_count"],
            record["original_row_count"],
            record["quality_score"],
            report.score,
        )
        self.activity.record("dataset.reset", f"{record['name']}: restored original data", dataset_id=dataset_id)
        return self.detail(dataset_id)

    # -- analysis -------------------------------------------------------

    def analysis(self, dataset_id: str) -> dict:
        return analytics.analyse(self.workspace(dataset_id).analysis_context)

    def _numeric_values(self, workspace: Workspace, column: str | None) -> pd.Series | None:
        if not column:
            return None
        if column not in workspace.typed.columns:
            raise ValidationFailed(f"Column '{column}' does not exist.")
        profile = workspace.profile.column(column)
        if profile.inferred_type != NUMERIC:
            raise ValidationFailed(f"'{column}' is not a numeric column, so it can only be counted.")
        return workspace.typed[column]

    def aggregate_chart(self, dataset_id: str, group_by: str, value: str | None, agg: str, top_n: int) -> dict:
        workspace = self.workspace(dataset_id)
        try:
            return analytics.aggregate(workspace.typed, group_by, self._numeric_values(workspace, value), agg, top_n)
        except analytics.AnalysisError as error:
            raise ValidationFailed(str(error)) from error

    def time_series_chart(self, dataset_id: str, date_column: str | None, value: str | None, agg: str, granularity: str) -> dict:
        workspace = self.workspace(dataset_id)
        date_column = date_column or workspace.roles.get("date")
        if not date_column:
            raise ValidationFailed("This dataset has no date column, so a time series cannot be produced.", code="no_date_column")
        if date_column not in workspace.typed.columns:
            raise ValidationFailed(f"Column '{date_column}' does not exist.")
        try:
            return analytics.time_series(workspace.typed[date_column], self._numeric_values(workspace, value), agg, granularity)
        except analytics.AnalysisError as error:
            raise ValidationFailed(str(error)) from error

    def distribution_chart(self, dataset_id: str, column: str, bins: int) -> dict:
        workspace = self.workspace(dataset_id)
        values = self._numeric_values(workspace, column)
        try:
            return {"column": column, **analytics.distribution(values, bins)}
        except analytics.AnalysisError as error:
            raise ValidationFailed(str(error)) from error

    def export_working_csv(self, dataset_id: str) -> bytes:
        return frame_to_csv_bytes(self.workspace(dataset_id).frame)

    def export_aggregate_csv(self, dataset_id: str, group_by: str, value: str | None, agg: str) -> bytes:
        result = self.aggregate_chart(dataset_id, group_by, value, agg, top_n=0)
        frame = pd.DataFrame(result["rows"], columns=["group", "value", "records", "share"])
        frame = frame.rename(
            columns={"group": group_by, "value": f"{result['aggregation']}_{value or 'records'}", "share": "share_percent"}
        )
        return frame_to_csv_bytes(frame)
