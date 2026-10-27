"""Dataset inspection and documented cleaning rules.

``profile_dataset`` describes the file exactly as it was received.
``clean_dataset`` then applies the rules below in order and records how many
rows or cells each rule changed, so every number in a report can be traced
back to a rule. The rules are also documented in docs/data-cleaning-rules.md.

C1  Trim spaces from every cell and treat placeholder text ("", "N/A",
    "null", "-", ...) as missing.
C2  Remove exact duplicate rows, keeping the first copy.
C3  Remove rows with a missing value in a required column.
C4  Parse order_date (ISO yyyy-mm-dd, or dd/mm/yyyy); remove rows whose date
    cannot be read or is not a real calendar date.
C5  Parse quantity; remove rows where it is not a whole number above zero.
C6  Parse unit_price (currency symbols and thousands separators are
    stripped); remove rows where it is not a number or is negative.
C7  Make category spellings consistent (e.g. "north" -> "North"), using the
    most common spelling of each value.
C8  Fill missing values in optional text columns with "Unknown".
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.services.csv_loader import OPTIONAL_COLUMNS, REQUIRED_COLUMNS

MISSING_TOKENS = {"", "na", "n/a", "nan", "null", "none", "-", "--", "?"}
CATEGORY_COLUMNS = ["product_category", "region", "channel", "customer_type"]
TEXT_FILL_VALUE = "Unknown"

RULES = {
    "C1": "Trim spaces and treat placeholder text (N/A, null, -) as missing",
    "C2": "Remove exact duplicate rows (first copy kept)",
    "C3": "Remove rows missing a required value (order_id, order_date, quantity, unit_price)",
    "C4": "Remove rows with an unreadable or impossible order_date",
    "C5": "Remove rows where quantity is not a whole number above zero",
    "C6": "Remove rows where unit_price is not a number or is negative",
    "C7": "Make category spellings consistent (most common spelling kept)",
    "C8": 'Fill missing optional text values with "Unknown"',
}


@dataclass
class CleaningResult:
    frame: pd.DataFrame
    steps: list[dict] = field(default_factory=list)
    rows_received: int = 0
    rows_removed: int = 0


def _is_missing(series: pd.Series) -> pd.Series:
    return series.isna() | series.astype(str).str.strip().str.lower().isin(MISSING_TOKENS)


def parse_dates(series: pd.Series) -> pd.Series:
    """ISO dates first; then UK day-first dates for anything left over."""
    text = series.astype(str).str.strip()
    iso = pd.to_datetime(text, format="%Y-%m-%d", errors="coerce")
    uk = pd.to_datetime(text, format="%d/%m/%Y", errors="coerce")
    return iso.fillna(uk)


def parse_numbers(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip().str.replace(r"[£$€,\s]", "", regex=True)
    return pd.to_numeric(text, errors="coerce")


def _infer_type(name: str, values: pd.Series) -> str:
    if name == "order_date":
        return "date"
    if name in ("quantity", "unit_price"):
        return "number"
    if values.empty:
        return "text"
    if parse_numbers(values).notna().mean() > 0.95:
        return "number"
    if values.nunique() <= max(20, len(values) * 0.05):
        return "category"
    return "text"


def profile_dataset(frame: pd.DataFrame) -> dict:
    """Inspect the dataset as received, before any cleaning."""
    rows = len(frame)
    columns = []
    total_missing = 0
    for name in frame.columns:
        series = frame[name]
        missing_mask = _is_missing(series)
        present = series[~missing_mask].astype(str).str.strip()
        missing = int(missing_mask.sum())
        total_missing += missing
        col_type = _infer_type(name, present)
        invalid = 0
        if name == "order_date":
            invalid = int(parse_dates(present).isna().sum())
        elif name == "quantity":
            numbers = parse_numbers(present)
            invalid = int((numbers.isna() | (numbers <= 0) | (numbers % 1 != 0)).sum())
        elif name == "unit_price":
            numbers = parse_numbers(present)
            invalid = int((numbers.isna() | (numbers < 0)).sum())
        columns.append(
            {
                "name": name,
                "type": col_type,
                "role": "required" if name in REQUIRED_COLUMNS else "optional" if name in OPTIONAL_COLUMNS else "extra",
                "missing": missing,
                "missing_pct": round(missing / rows * 100, 2) if rows else 0.0,
                "invalid": invalid,
                "unique": int(present.nunique()),
                "examples": [str(v)[:40] for v in present.drop_duplicates().head(3)],
            }
        )
    duplicate_rows = int(frame.apply(lambda c: c.astype(str).str.strip()).duplicated().sum())
    cells = rows * len(frame.columns)
    return {
        "rows": rows,
        "columns": len(frame.columns),
        "column_names": list(frame.columns),
        "duplicate_rows": duplicate_rows,
        "missing_cells": total_missing,
        "completeness_pct": round((1 - total_missing / cells) * 100, 2) if cells else 0.0,
        "column_profile": columns,
    }


def _record(steps: list[dict], rule: str, rows_removed: int = 0, cells_changed: int = 0, detail: str = "") -> None:
    steps.append(
        {
            "rule": rule,
            "description": RULES[rule],
            "rows_removed": int(rows_removed),
            "cells_changed": int(cells_changed),
            "detail": detail,
        }
    )


def clean_dataset(frame: pd.DataFrame) -> CleaningResult:
    """Apply rules C1-C8 and return the cleaned, typed DataFrame."""
    df = frame.copy()
    received = len(df)
    steps: list[dict] = []

    # C1: trim and standardise missing values.
    changed = 0
    for col in df.columns:
        original = df[col]
        trimmed = original.astype(str).str.strip()
        missing = _is_missing(original)
        trimmed = trimmed.mask(missing, np.nan)
        changed += int(((trimmed != original) & ~(trimmed.isna() & original.isna())).sum())
        df[col] = trimmed
    _record(steps, "C1", cells_changed=changed)

    # C2: exact duplicates (after trimming, so " A" and "A" match).
    dup_mask = df.duplicated(keep="first")
    df = df[~dup_mask]
    _record(steps, "C2", rows_removed=dup_mask.sum())

    # C3: required values present.
    missing_required = df[REQUIRED_COLUMNS].isna().any(axis=1)
    by_column = {c: int(df[c].isna().sum()) for c in REQUIRED_COLUMNS if df[c].isna().any()}
    df = df[~missing_required]
    _record(
        steps,
        "C3",
        rows_removed=missing_required.sum(),
        detail=", ".join(f"{c}: {n}" for c, n in by_column.items()),
    )

    # C4: dates.
    dates = parse_dates(df["order_date"])
    bad_dates = dates.isna()
    df = df[~bad_dates].assign(order_date=dates[~bad_dates])
    _record(steps, "C4", rows_removed=bad_dates.sum())

    # C5: quantity.
    qty = parse_numbers(df["quantity"])
    bad_qty = qty.isna() | (qty <= 0) | (qty % 1 != 0)
    df = df[~bad_qty].assign(quantity=qty[~bad_qty].astype("int64"))
    _record(steps, "C5", rows_removed=bad_qty.sum())

    # C6: unit price.
    price = parse_numbers(df["unit_price"])
    bad_price = price.isna() | (price < 0)
    df = df[~bad_price].assign(unit_price=price[~bad_price].astype(float))
    _record(steps, "C6", rows_removed=bad_price.sum())

    # C7: consistent category spellings.
    respelled = 0
    for col in [c for c in CATEGORY_COLUMNS if c in df.columns]:
        values = df[col].dropna()
        if values.empty:
            continue
        canonical = values.groupby(values.str.lower()).agg(lambda s: s.value_counts().index[0])
        mapped = df[col].map(lambda v: canonical.get(v.lower(), v) if isinstance(v, str) else v)
        respelled += int(((mapped != df[col]) & df[col].notna()).sum())
        df[col] = mapped
    _record(steps, "C7", cells_changed=respelled)

    # C8: fill optional text columns.
    filled = 0
    for col in [c for c in df.columns if c not in REQUIRED_COLUMNS]:
        n = int(df[col].isna().sum())
        if n:
            df[col] = df[col].fillna(TEXT_FILL_VALUE)
            filled += n
    _record(steps, "C8", cells_changed=filled)

    df = df.reset_index(drop=True)
    df["revenue"] = (df["quantity"] * df["unit_price"]).round(2)
    return CleaningResult(frame=df, steps=steps, rows_received=received, rows_removed=received - len(df))
