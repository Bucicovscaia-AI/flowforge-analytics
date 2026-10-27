"""Registry of the bundled synthetic sample datasets (see sample-data/)."""

from __future__ import annotations

from pathlib import Path

SAMPLES = [
    {
        "id": "retail-2026",
        "file": "retail_sales_2026_synthetic.csv",
        "name": "Retail sales, Jan–Jun 2026",
        "description": "About 1,150 order lines across five categories, four regions and three channels, "
        "with deliberate quality issues (duplicates, blanks, bad dates, negative quantities).",
    },
    {
        "id": "web-minimal",
        "file": "web_orders_minimal_synthetic.csv",
        "name": "Web orders, required columns only",
        "description": "Order id, date, quantity and price only. Shows how KPIs that need "
        "category or region are reported as unavailable.",
    },
]


def list_samples(sample_dir: Path) -> list[dict]:
    out = []
    for sample in SAMPLES:
        path = sample_dir / sample["file"]
        if path.exists():
            out.append({**sample, "size_bytes": path.stat().st_size, "synthetic": True})
    return out


def sample_path(sample_dir: Path, sample_id: str) -> Path | None:
    for sample in SAMPLES:
        if sample["id"] == sample_id:
            path = sample_dir / sample["file"]
            return path if path.exists() else None
    return None
