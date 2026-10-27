"""File-based storage for analysis results and generated reports.

Only derived results are stored: profiles, KPIs, observations, a 25-row
preview of the cleaned data and the generated PDFs. The uploaded file itself
is never written to disk.

JSON files on disk keep the project free of database infrastructure, which is
enough for a single-user demo. A multi-user deployment would swap this class
for a database without changing the routes.
"""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path

ID_PATTERN = re.compile(r"^[a-z]{3}_[0-9a-f]{12}$")


class Store:
    def __init__(self, root: Path, max_analyses: int = 50):
        self.root = root
        self.analyses_dir = root / "analyses"
        self.reports_dir = root / "reports"
        self.index_file = self.reports_dir / "index.json"
        self.max_analyses = max_analyses
        self._lock = threading.Lock()
        self.analyses_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def valid_id(value: str) -> bool:
        # Ids become file names, so anything else (e.g. "../") is refused.
        return bool(ID_PATTERN.match(value))

    # Analyses -----------------------------------------------------------
    def save_analysis(self, analysis: dict) -> None:
        with self._lock:
            path = self.analyses_dir / f"{analysis['id']}.json"
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(analysis), encoding="utf-8")
            tmp.replace(path)
            files = sorted(self.analyses_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
            for old in files[: max(0, len(files) - self.max_analyses)]:
                old.unlink(missing_ok=True)

    def get_analysis(self, analysis_id: str) -> dict | None:
        if not self.valid_id(analysis_id):
            return None
        path = self.analyses_dir / f"{analysis_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_analyses(self) -> list[dict]:
        out = []
        for path in self.analyses_dir.glob("*.json"):
            a = json.loads(path.read_text(encoding="utf-8"))
            out.append(
                {
                    "id": a["id"],
                    "created_at": a["created_at"],
                    "file_name": a["dataset"]["file_name"],
                    "synthetic": a["dataset"]["synthetic"],
                    "rows_analysed": a["quality"]["rows_analysed"],
                    "total_revenue": a["kpis"]["summary"]["total_revenue"],
                }
            )
        return sorted(out, key=lambda a: a["created_at"], reverse=True)

    # Reports ------------------------------------------------------------
    def _read_index(self) -> list[dict]:
        if not self.index_file.exists():
            return []
        return json.loads(self.index_file.read_text(encoding="utf-8"))

    def _write_index(self, items: list[dict]) -> None:
        tmp = self.index_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(items, indent=1), encoding="utf-8")
        tmp.replace(self.index_file)

    def add_report(self, meta: dict, pdf: bytes) -> None:
        with self._lock:
            (self.reports_dir / f"{meta['id']}.pdf").write_bytes(pdf)
            items = self._read_index()
            items.insert(0, meta)
            self._write_index(items)

    def update_report(self, report_id: str, **changes) -> dict | None:
        with self._lock:
            items = self._read_index()
            for item in items:
                if item["id"] == report_id:
                    item.update(changes)
                    self._write_index(items)
                    return item
        return None

    def list_reports(self) -> list[dict]:
        return self._read_index()

    def get_report(self, report_id: str) -> dict | None:
        if not self.valid_id(report_id):
            return None
        return next((r for r in self._read_index() if r["id"] == report_id), None)

    def report_path(self, report_id: str) -> Path | None:
        if not self.valid_id(report_id):
            return None
        path = self.reports_dir / f"{report_id}.pdf"
        return path if path.exists() else None

    def delete_report(self, report_id: str) -> bool:
        if not self.valid_id(report_id):
            return False
        with self._lock:
            items = self._read_index()
            remaining = [r for r in items if r["id"] != report_id]
            if len(remaining) == len(items):
                return False
            self._write_index(remaining)
            (self.reports_dir / f"{report_id}.pdf").unlink(missing_ok=True)
            return True
