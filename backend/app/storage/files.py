"""Local file storage for dataset copies and generated reports.

File paths are built only from server-generated identifiers, never from
user-supplied filenames, so uploaded names cannot influence where data is
written or read.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pandas as pd

from app.engine.loading import read_stored_csv

_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")

ORIGINAL = "original.csv"
WORKING = "working.csv"


def validate_id(identifier: str) -> str:
    if not _ID_PATTERN.match(identifier or ""):
        raise ValueError("Invalid identifier.")
    return identifier


class DatasetFileStore:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def directory(self, dataset_id: str) -> Path:
        return self.root / validate_id(dataset_id)

    def write_initial(self, dataset_id: str, frame: pd.DataFrame) -> int:
        """Store the parsed upload as both the preserved original and the working copy."""
        directory = self.directory(dataset_id)
        directory.mkdir(parents=True, exist_ok=True)
        original = directory / ORIGINAL
        frame.to_csv(original, index=False, encoding="utf-8")
        shutil.copyfile(original, directory / WORKING)
        return original.stat().st_size

    def write_working(self, dataset_id: str, frame: pd.DataFrame) -> None:
        directory = self.directory(dataset_id)
        temporary = directory / f"{WORKING}.tmp"
        frame.to_csv(temporary, index=False, encoding="utf-8")
        temporary.replace(directory / WORKING)

    def reset_working(self, dataset_id: str) -> None:
        directory = self.directory(dataset_id)
        shutil.copyfile(directory / ORIGINAL, directory / WORKING)

    def working_path(self, dataset_id: str) -> Path:
        return self.directory(dataset_id) / WORKING

    def read_working(self, dataset_id: str) -> pd.DataFrame:
        return read_stored_csv(self.working_path(dataset_id))

    def exists(self, dataset_id: str) -> bool:
        return self.working_path(dataset_id).is_file()

    def delete(self, dataset_id: str) -> None:
        shutil.rmtree(self.directory(dataset_id), ignore_errors=True)


class ReportFileStore:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def path(self, report_id: str, extension: str) -> Path:
        return self.root / validate_id(report_id) / f"report.{extension}"

    def write(self, report_id: str, extension: str, content: bytes) -> Path:
        path = self.path(report_id, extension)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def delete(self, report_id: str) -> None:
        shutil.rmtree(self.root / validate_id(report_id), ignore_errors=True)
