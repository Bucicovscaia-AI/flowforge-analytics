"""SQLite persistence for dataset metadata, cleaning history, reports and automation runs.

Repositories in `repositories.py` are the only code that issues SQL, so the
storage engine can be replaced without touching services or routes.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source_filename TEXT,
    is_sample INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    original_row_count INTEGER NOT NULL,
    row_count INTEGER NOT NULL,
    column_count INTEGER NOT NULL,
    size_bytes INTEGER NOT NULL,
    encoding TEXT,
    delimiter TEXT,
    quality_score REAL,
    quality_grade TEXT,
    column_mapping TEXT NOT NULL DEFAULT '{}',
    warnings TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS dataset_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    operation TEXT NOT NULL,
    params TEXT NOT NULL,
    summary TEXT NOT NULL,
    rows_before INTEGER NOT NULL,
    rows_after INTEGER NOT NULL,
    quality_before REAL,
    quality_after REAL,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    dataset_id TEXT,
    dataset_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL,
    insight_mode TEXT,
    record_count INTEGER,
    formats TEXT NOT NULL DEFAULT '[]',
    error TEXT
);

CREATE TABLE IF NOT EXISTS automation_runs (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    trigger TEXT NOT NULL,
    dataset_id TEXT,
    report_id TEXT,
    status TEXT NOT NULL,
    http_status INTEGER,
    message TEXT NOT NULL,
    duration_ms INTEGER,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    pdf_downloaded_at TEXT,
    confirmation_status TEXT,
    confirmation_message TEXT,
    confirmed_at TEXT
);

CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    message TEXT NOT NULL,
    dataset_id TEXT,
    report_id TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_operations_dataset ON dataset_operations(dataset_id);
CREATE INDEX IF NOT EXISTS idx_reports_dataset ON reports(dataset_id);
CREATE INDEX IF NOT EXISTS idx_activity_created ON activity(created_at);
CREATE INDEX IF NOT EXISTS idx_runs_report ON automation_runs(report_id);
"""

# Columns added after the first release, applied to databases created before them.
MIGRATIONS = {
    "automation_runs": {
        "pdf_downloaded_at": "TEXT",
        "confirmation_status": "TEXT",
        "confirmation_message": "TEXT",
        "confirmed_at": "TEXT",
    },
}


class Database:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            for table, columns in MIGRATIONS.items():
                existing = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
                if not existing:
                    continue
                for name, kind in columns.items():
                    if name not in existing:
                        connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {kind}")
            connection.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
