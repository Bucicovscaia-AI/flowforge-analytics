"""Data access for SQLite tables. Rows are returned as plain dictionaries."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from app.storage.database import Database


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _row(row: sqlite3.Row | None, json_fields: tuple[str, ...] = ()) -> dict | None:
    if row is None:
        return None
    data = dict(row)
    for name in json_fields:
        if name in data and data[name] is not None:
            data[name] = json.loads(data[name])
    return data


class DatasetRepository:
    JSON_FIELDS = ("column_mapping", "warnings")

    def __init__(self, database: Database):
        self.database = database

    def create(self, record: dict) -> dict:
        record = {**record}
        record["column_mapping"] = json.dumps(record.get("column_mapping", {}))
        record["warnings"] = json.dumps(record.get("warnings", []))
        columns = ", ".join(record)
        placeholders = ", ".join(f":{name}" for name in record)
        with self.database.connect() as connection:
            connection.execute(f"INSERT INTO datasets ({columns}) VALUES ({placeholders})", record)  # noqa: S608 (column names are defined in code, values are bound parameters)
        return self.get(record["id"])

    def get(self, dataset_id: str) -> dict | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
        return _row(row, self.JSON_FIELDS)

    def list(self) -> list[dict]:
        with self.database.connect() as connection:
            rows = connection.execute("SELECT * FROM datasets ORDER BY created_at DESC").fetchall()
        return [_row(row, self.JSON_FIELDS) for row in rows]

    _UPDATABLE = {"name", "status", "row_count", "column_count", "quality_score", "quality_grade", "column_mapping", "updated_at"}

    def update(self, dataset_id: str, **fields) -> dict | None:
        fields = {name: value for name, value in fields.items() if name in self._UPDATABLE}
        if "column_mapping" in fields:
            fields["column_mapping"] = json.dumps(fields["column_mapping"])
        fields.setdefault("updated_at", utc_now())
        assignments = ", ".join(f"{name} = :{name}" for name in fields)
        with self.database.connect() as connection:
            connection.execute(f"UPDATE datasets SET {assignments} WHERE id = :id", {**fields, "id": dataset_id})  # noqa: S608 (column names are defined in code, values are bound parameters)
        return self.get(dataset_id)

    def delete(self, dataset_id: str) -> bool:
        with self.database.connect() as connection:
            cursor = connection.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
        return cursor.rowcount > 0

    def add_operation(
        self,
        dataset_id: str,
        operation: str,
        params: dict,
        summary: str,
        rows_before: int,
        rows_after: int,
        quality_before: float | None,
        quality_after: float | None,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO dataset_operations
                   (dataset_id, operation, params, summary, rows_before, rows_after, quality_before, quality_after, applied_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    dataset_id,
                    operation,
                    json.dumps(params),
                    summary,
                    rows_before,
                    rows_after,
                    quality_before,
                    quality_after,
                    utc_now(),
                ),
            )

    def operations(self, dataset_id: str) -> list[dict]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM dataset_operations WHERE dataset_id = ? ORDER BY id", (dataset_id,)
            ).fetchall()
        return [_row(row, ("params",)) for row in rows]


class ReportRepository:
    def __init__(self, database: Database):
        self.database = database

    def create(self, record: dict) -> dict:
        record = {**record, "formats": json.dumps(record.get("formats", []))}
        columns = ", ".join(record)
        placeholders = ", ".join(f":{name}" for name in record)
        with self.database.connect() as connection:
            connection.execute(f"INSERT INTO reports ({columns}) VALUES ({placeholders})", record)  # noqa: S608 (column names are defined in code, values are bound parameters)
        return self.get(record["id"])

    def get(self, report_id: str) -> dict | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        return _row(row, ("formats",))

    def list(self, dataset_id: str | None = None, limit: int = 100) -> list[dict]:
        query = "SELECT * FROM reports"
        params: tuple = ()
        if dataset_id:
            query += " WHERE dataset_id = ?"
            params = (dataset_id,)
        query += " ORDER BY created_at DESC, rowid DESC LIMIT ?"
        with self.database.connect() as connection:
            rows = connection.execute(query, (*params, limit)).fetchall()
        return [_row(row, ("formats",)) for row in rows]

    def delete(self, report_id: str) -> bool:
        with self.database.connect() as connection:
            cursor = connection.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        return cursor.rowcount > 0


class AutomationRepository:
    def __init__(self, database: Database):
        self.database = database

    def create(self, record: dict) -> dict:
        record = {**record, "payload": json.dumps(record["payload"])}
        columns = ", ".join(record)
        placeholders = ", ".join(f":{name}" for name in record)
        with self.database.connect() as connection:
            connection.execute(f"INSERT INTO automation_runs ({columns}) VALUES ({placeholders})", record)  # noqa: S608 (column names are defined in code, values are bound parameters)
            row = connection.execute("SELECT * FROM automation_runs WHERE id = ?", (record["id"],)).fetchone()
        return _row(row, ("payload",))

    def list(self, limit: int = 50) -> list[dict]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM automation_runs ORDER BY created_at DESC, rowid DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_row(row, ("payload",)) for row in rows]

    def get(self, run_id: str) -> dict | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM automation_runs WHERE id = ?", (run_id,)).fetchone()
        return _row(row, ("payload",))

    def latest_accepted_for_report(self, report_id: str) -> dict | None:
        """The most recent event for a report that the webhook accepted and Make.com has not reported as failed."""
        with self.database.connect() as connection:
            row = connection.execute(
                """SELECT * FROM automation_runs
                   WHERE report_id = ? AND status = 'delivered' AND COALESCE(confirmation_status, '') != 'failed'
                   ORDER BY created_at DESC, rowid DESC LIMIT 1""",
                (report_id,),
            ).fetchone()
        return _row(row, ("payload",))

    def finish(
        self,
        run_id: str,
        *,
        status: str,
        http_status: int | None,
        message: str,
        duration_ms: int | None,
        confirmation_status: str | None,
    ) -> dict | None:
        with self.database.connect() as connection:
            # A fast scenario can confirm before this update runs, so an existing confirmation is kept.
            connection.execute(
                """UPDATE automation_runs SET status = ?, http_status = ?, message = ?, duration_ms = ?,
                   confirmation_status = COALESCE(confirmation_status, ?) WHERE id = ?""",
                (status, http_status, message, duration_ms, confirmation_status, run_id),
            )
        return self.get(run_id)

    def mark_pdf_downloaded(self, run_id: str) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE automation_runs SET pdf_downloaded_at = COALESCE(pdf_downloaded_at, ?) WHERE id = ?", (utc_now(), run_id)
            )

    def confirm(self, run_id: str, status: str, message: str | None) -> dict | None:
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE automation_runs SET confirmation_status = ?, confirmation_message = ?, confirmed_at = ? WHERE id = ?",
                (status, message, utc_now(), run_id),
            )
        return self.get(run_id)


class ActivityRepository:
    def __init__(self, database: Database):
        self.database = database

    def record(self, kind: str, message: str, dataset_id: str | None = None, report_id: str | None = None) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO activity (kind, message, dataset_id, report_id, created_at) VALUES (?, ?, ?, ?, ?)",
                (kind, message, dataset_id, report_id, utc_now()),
            )

    def list(self, limit: int = 20, dataset_id: str | None = None) -> list[dict]:
        query = "SELECT * FROM activity"
        params: tuple = ()
        if dataset_id:
            query += " WHERE dataset_id = ?"
            params = (dataset_id,)
        query += " ORDER BY id DESC LIMIT ?"
        with self.database.connect() as connection:
            rows = connection.execute(query, (*params, limit)).fetchall()
        return [dict(row) for row in rows]
