"""The analysis pipeline: inspect -> clean -> calculate KPIs -> observe.

Routes call ``run_analysis`` and store its result. Keeping the steps in one
function makes the whole pipeline testable without HTTP.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.services.cleaning import clean_dataset, profile_dataset
from app.services.csv_loader import LoadedDataset
from app.services.kpis import calculate_kpis
from app.services.observations import build_observations

PREVIEW_ROWS = 25


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _preview(frame) -> dict:
    head = frame.head(PREVIEW_ROWS).copy()
    if "order_date" in head:
        head["order_date"] = head["order_date"].dt.strftime("%Y-%m-%d")
    return {"columns": list(head.columns), "rows": head.astype(object).where(head.notna(), None).to_dict(orient="records")}


def run_analysis(loaded: LoadedDataset, *, synthetic: bool, sample_id: str | None = None) -> dict:
    profile = profile_dataset(loaded.frame)
    cleaned = clean_dataset(loaded.frame)
    kpis = calculate_kpis(cleaned.frame)
    received = cleaned.rows_received
    analysed = len(cleaned.frame)
    quality = {
        "rows_received": received,
        "rows_analysed": analysed,
        "rows_removed": cleaned.rows_removed,
        "duplicate_rows": profile["duplicate_rows"],
        "missing_cells": profile["missing_cells"],
        "completeness_pct": profile["completeness_pct"],
        # Share of received rows that passed every cleaning rule.
        "quality_score": round(analysed / received * 100, 2) if received else 0.0,
    }
    return {
        "id": new_id("ana"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "file_name": loaded.file_name,
            "size_bytes": loaded.size_bytes,
            "encoding": loaded.encoding,
            "columns": list(loaded.frame.columns),
            "original_columns": loaded.original_columns,
            "renamed_columns": loaded.renamed_columns,
            "synthetic": synthetic,
            "sample_id": sample_id,
        },
        "profile": profile,
        "quality": quality,
        "cleaning_steps": cleaned.steps,
        "kpis": kpis,
        "observations": build_observations(kpis, quality),
        "preview": _preview(cleaned.frame),
        "insights": None,
    }
