"""Safe CSV parsing.

Uploaded bytes are decoded and parsed as plain text only; nothing in a file is
ever executed or evaluated. Every cell is read as a string so that type
inference (see `profiling.py`) is explicit and repeatable rather than left to
pandas' parser heuristics.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field

import pandas as pd

# Cell values treated as missing. Whitespace-only cells are also treated as missing.
MISSING_MARKERS = ["", "NA", "N/A", "n/a", "na", "null", "NULL", "Null", "None", "none", "NaN", "nan", "#N/A"]

_CANDIDATE_DELIMITERS = [",", ";", "\t", "|"]
_ENCODINGS = ("utf-8-sig", "cp1252")


class CSVValidationError(ValueError):
    """Raised when a file cannot be accepted as a CSV dataset."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ParsedCSV:
    frame: pd.DataFrame
    encoding: str
    delimiter: str
    warnings: list[str] = field(default_factory=list)


def _decode(data: bytes) -> tuple[str, str]:
    for encoding in _ENCODINGS:
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise CSVValidationError(
        "unsupported_encoding",
        "The file is not valid UTF-8 or Windows-1252 text. Save it as UTF-8 CSV and try again.",
    )


def _detect_delimiter(text: str) -> str:
    sample = "\n".join(text.splitlines()[:50])
    try:
        return csv.Sniffer().sniff(sample, delimiters="".join(_CANDIDATE_DELIMITERS)).delimiter
    except csv.Error:
        header = sample.splitlines()[0] if sample else ""
        counts = {delimiter: header.count(delimiter) for delimiter in _CANDIDATE_DELIMITERS}
        best = max(counts, key=counts.get)
        return best if counts[best] > 0 else ","


def _clean_header(columns: list[str], warnings: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: dict[str, int] = {}
    for position, raw in enumerate(columns, start=1):
        name = re.sub(r"\s+", " ", str(raw)).strip()
        if not name or name.lower().startswith("unnamed:"):
            name = f"column_{position}"
            warnings.append(f"Column {position} had no header and was named '{name}'.")
        base = name
        if name.lower() in seen:
            seen[base.lower()] += 1
            name = f"{base}_{seen[base.lower()]}"
            warnings.append(f"Duplicate column name '{base}' was renamed to '{name}'.")
        seen.setdefault(name.lower(), 1)
        cleaned.append(name)
    return cleaned


def parse_csv_bytes(data: bytes, *, max_rows: int, max_columns: int) -> ParsedCSV:
    """Parse raw CSV bytes into a string-typed DataFrame or raise CSVValidationError."""
    if not data or not data.strip():
        raise CSVValidationError("empty_file", "The file is empty.")
    if b"\x00" in data[:8192]:
        raise CSVValidationError("binary_content", "The file appears to be binary, not a text CSV file.")

    text, encoding = _decode(data)
    delimiter = _detect_delimiter(text)
    warnings: list[str] = []

    try:
        raw_header = next(csv.reader(io.StringIO(text.lstrip("\r\n")), delimiter=delimiter))
    except (StopIteration, csv.Error) as exc:
        raise CSVValidationError("malformed_csv", "The header row could not be read.") from exc
    if len(raw_header) > max_columns:
        raise CSVValidationError("too_many_columns", f"The file has {len(raw_header)} columns; the limit is {max_columns}.")
    header = _clean_header(raw_header, warnings)

    try:
        frame = pd.read_csv(
            io.StringIO(text),
            sep=delimiter,
            header=None,
            dtype=str,
            keep_default_na=False,
            na_values=MISSING_MARKERS,
            skip_blank_lines=True,
            on_bad_lines="error",
            engine="python",
        )
    except pd.errors.EmptyDataError as exc:
        raise CSVValidationError("empty_file", "The file contains no readable data.") from exc
    except (pd.errors.ParserError, csv.Error) as exc:
        detail = str(exc).split("\n")[0]
        raise CSVValidationError(
            "malformed_csv",
            f"The file could not be parsed as CSV: {detail}. Check for unbalanced quotes or rows with extra fields.",
        ) from exc

    if frame.shape[1] != len(header):
        raise CSVValidationError(
            "malformed_csv",
            f"The header has {len(header)} columns but the data has {frame.shape[1]}. Check for rows with extra fields.",
        )
    frame = frame.iloc[1:].reset_index(drop=True)
    frame.columns = header
    if frame.shape[1] == 1 and delimiter == "," and len(text.splitlines()) > 1:
        warnings.append("Only one column was detected. If this is unexpected, check the file's delimiter.")

    # Whitespace-only cells count as missing; other values keep their original spacing
    # so that formatting problems remain visible to the data quality checks.
    frame = frame.apply(lambda column: column.mask(column.str.strip() == "", None))
    frame = frame.dropna(how="all").reset_index(drop=True)

    if frame.empty:
        raise CSVValidationError("no_rows", "The file has a header row but no data rows.")
    if len(frame) > max_rows:
        raise CSVValidationError("too_many_rows", f"The file has {len(frame):,} rows; the limit is {max_rows:,}.")
    return ParsedCSV(frame=frame, encoding=encoding.replace("-sig", ""), delimiter=delimiter, warnings=warnings)


def read_stored_csv(path) -> pd.DataFrame:
    """Read a CSV previously written by the dataset store (UTF-8, comma-separated)."""
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""], encoding="utf-8")
