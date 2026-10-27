"""Safe CSV loading and validation.

Every check here runs on the server, even though the browser runs similar
checks first, because anything done in the browser can be bypassed.

The file is parsed with every cell read as text (``dtype=str``). Types are
converted later by the documented cleaning rules, so nothing in the file can
make pandas guess types or evaluate content.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass

import pandas as pd

# Columns the analysis needs. Without them no core KPI can be calculated.
REQUIRED_COLUMNS = ["order_id", "order_date", "quantity", "unit_price"]
# Columns that unlock extra breakdowns when present.
OPTIONAL_COLUMNS = ["product", "product_category", "region", "channel", "customer_type"]

# Common alternative header names, mapped to the names used internally.
COLUMN_ALIASES = {
    "order": "order_id",
    "order_number": "order_id",
    "order_no": "order_id",
    "orderid": "order_id",
    "transaction_id": "order_id",
    "date": "order_date",
    "transaction_date": "order_date",
    "orderdate": "order_date",
    "qty": "quantity",
    "units": "quantity",
    "price": "unit_price",
    "unitprice": "unit_price",
    "category": "product_category",
    "product_name": "product",
    "item": "product",
    "sales_channel": "channel",
    "customer_segment": "customer_type",
    "segment": "customer_type",
}

ALLOWED_CONTENT_TYPES = {
    "",
    "text/csv",
    "text/plain",
    "application/csv",
    "application/vnd.ms-excel",  # what Windows browsers report for .csv
    "application/octet-stream",
}


class DatasetError(Exception):
    """A problem with the uploaded file that the user can fix.

    ``status_code`` is the HTTP status the API returns; ``problems`` lists
    every readable reason so the interface can show them all at once.
    """

    def __init__(self, message: str, status_code: int = 422, problems: list[str] | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.problems = problems or [message]


@dataclass
class LoadedDataset:
    frame: pd.DataFrame
    file_name: str
    size_bytes: int
    encoding: str
    original_columns: list[str]
    renamed_columns: dict[str, str]


def normalise_header(name: str) -> str:
    """'Order Date ' -> 'order_date'; aliases such as 'Qty' -> 'quantity'."""
    cleaned = re.sub(r"[^0-9a-z]+", "_", str(name).strip().lower()).strip("_")
    return COLUMN_ALIASES.get(cleaned, cleaned)


def _safe_file_name(name: str | None) -> str:
    # Keep only the final path part and printable characters: file names are
    # shown back to the user and written into reports.
    base = re.split(r"[\\/]", name or "upload.csv")[-1]
    base = re.sub(r"[^\w.\- ()]", "_", base).strip() or "upload.csv"
    return base[:120]


def _decode(raw: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise DatasetError("The file is not readable text. Save it as CSV (UTF-8) and try again.")


def load_csv(
    raw: bytes,
    file_name: str | None,
    content_type: str | None,
    *,
    max_bytes: int,
    max_rows: int,
    max_columns: int,
) -> LoadedDataset:
    """Validate the upload and return it as a text-only DataFrame."""
    name = _safe_file_name(file_name)
    if not name.lower().endswith(".csv"):
        raise DatasetError(f'"{name}" is not a CSV file. Export the data as .csv and try again.', 415)
    media_type = (content_type or "").split(";")[0].strip().lower()
    if media_type not in ALLOWED_CONTENT_TYPES:
        raise DatasetError(f"Files of type {media_type} are not accepted. Upload a CSV file.", 415)
    if len(raw) == 0:
        raise DatasetError("The file is empty.", 400)
    if len(raw) > max_bytes:
        raise DatasetError(f"The file is larger than {max_bytes // (1024 * 1024)} MB.", 413)
    if b"\x00" in raw[:8192]:
        raise DatasetError("The file looks like a binary file (for example a spreadsheet), not a CSV.", 415)

    text, encoding = _decode(raw)
    if not text.strip():
        raise DatasetError("The file contains no data.", 400)

    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","

    # The standard csv module is used (strict mode) instead of pandas'
    # parser, because pandas silently drops or shifts cells when a row has
    # the wrong number of fields. Here such a row is an error the user sees.
    reader = csv.reader(io.StringIO(text), delimiter=delimiter, skipinitialspace=True, strict=True)
    try:
        header = next(reader)
        if len(header) > max_columns:
            raise DatasetError(f"The file has {len(header)} columns; the limit is {max_columns}.")
        rows: list[list[str]] = []
        for row in reader:
            if not row or all(not cell.strip() for cell in row):
                continue  # blank lines are ignored
            if len(row) != len(header):
                raise DatasetError(
                    f"The CSV is malformed: line {reader.line_num} has {len(row)} fields but the header has {len(header)}."
                )
            rows.append(row)
            if len(rows) > max_rows:
                raise DatasetError(f"The file has more than {max_rows:,} rows. Upload a smaller extract.", 413)
    except StopIteration:
        raise DatasetError("The file has no header row or data.", 400) from None
    except csv.Error as exc:
        raise DatasetError(f"The CSV is malformed and could not be read (line {reader.line_num}: {exc}).") from None

    if not rows:
        raise DatasetError("The file has a header row but no data rows.")
    frame = pd.DataFrame(rows, columns=header, dtype=str)

    original = [str(c) for c in frame.columns]
    normalised = [normalise_header(c) for c in original]
    problems: list[str] = []
    if any(not c or c.startswith("unnamed") for c in normalised):
        problems.append("One or more columns have no header name.")
    duplicates = sorted({c for c in normalised if normalised.count(c) > 1 and c})
    if duplicates:
        problems.append(f"These columns appear more than once: {', '.join(duplicates)}.")
    missing = [c for c in REQUIRED_COLUMNS if c not in normalised]
    if missing:
        problems.append(
            f"Required columns are missing: {', '.join(missing)}. "
            f"Found: {', '.join(original)}."
        )
    if problems:
        raise DatasetError(problems[0], 422, problems)

    frame.columns = normalised
    renamed = {o: n for o, n in zip(original, normalised) if o != n}
    return LoadedDataset(
        frame=frame,
        file_name=name,
        size_bytes=len(raw),
        encoding="UTF-8" if encoding == "utf-8-sig" else "Windows-1252",
        original_columns=original,
        renamed_columns=renamed,
    )
