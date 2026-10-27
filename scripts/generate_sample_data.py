"""Generate the synthetic FlowForge demonstration dataset.

The output is fabricated retail order data. It does not describe any real
business or customer. A fixed random seed keeps the file reproducible, so the
same CSV is produced every time the script runs.

A small number of deliberate data quality problems are injected (duplicate
rows, missing and inconsistently formatted region values, unreadable dates)
so that the data quality and cleaning features have something to find.

Usage:
    python scripts/generate_sample_data.py [output_path]
"""

from __future__ import annotations

import csv
import random
import sys
from datetime import date, timedelta
from pathlib import Path

SEED = 20250101
START = date(2025, 1, 1)
END = date(2025, 12, 31)
ORDER_COUNT = 1200

# (product, category, base unit price)
CATALOGUE = [
    ("Wireless Earbuds", "Electronics", 59.99),
    ("Bluetooth Speaker", "Electronics", 44.50),
    ("USB-C Charger", "Electronics", 19.99),
    ("Smart Watch", "Electronics", 149.00),
    ("Laptop Stand", "Office", 34.99),
    ("Desk Organiser", "Office", 18.75),
    ("Ergonomic Chair", "Office", 189.00),
    ("Notebook Set", "Office", 9.50),
    ("Running Shoes", "Sports", 79.99),
    ("Yoga Mat", "Sports", 24.99),
    ("Water Bottle", "Sports", 12.49),
    ("Resistance Bands", "Sports", 15.99),
    ("Coffee Grinder", "Home & Kitchen", 64.00),
    ("Cast Iron Pan", "Home & Kitchen", 39.90),
    ("Glass Storage Set", "Home & Kitchen", 27.50),
    ("Scented Candle", "Home & Kitchen", 14.99),
    ("Face Moisturiser", "Beauty", 22.00),
    ("Hair Dryer", "Beauty", 54.99),
    ("Lip Balm Trio", "Beauty", 7.99),
    ("Bamboo Toothbrush Pack", "Beauty", 6.49),
]

REGIONS = ["North", "South", "East", "West", "Central"]
REGION_WEIGHTS = [0.22, 0.24, 0.18, 0.20, 0.16]
CHANNELS = ["Online", "In-store", "Marketplace"]
CHANNEL_WEIGHTS = [0.55, 0.30, 0.15]
STATUSES = ["Completed", "Returned", "Cancelled", "Pending"]
STATUS_WEIGHTS = [0.88, 0.05, 0.04, 0.03]

# Relative order volume by month: quieter start of year, Q4 peak.
MONTH_WEIGHT = {1: 0.75, 2: 0.7, 3: 0.85, 4: 0.9, 5: 0.95, 6: 1.0,
                7: 1.0, 8: 0.95, 9: 1.0, 10: 1.1, 11: 1.35, 12: 1.5}

FIELDS = [
    "order_id", "order_date", "product", "category", "quantity",
    "unit_price", "revenue", "region", "channel", "order_status",
]


def _order_dates(rng: random.Random, count: int) -> list[date]:
    """Spread orders across the year in proportion to month and weekday weights, with mild daily noise."""
    days = [START + timedelta(days=offset) for offset in range((END - START).days + 1)]
    weights = [MONTH_WEIGHT[day.month] * (1.15 if day.weekday() >= 5 else 1.0) for day in days]
    scale = count / sum(weights)
    dates: list[date] = []
    for day, weight in zip(days, weights):
        expected = weight * scale
        dates.extend([day] * max(0, round(rng.gauss(expected, expected ** 0.5 * 0.6))))
    return dates


def build_rows() -> list[dict[str, str]]:
    rng = random.Random(SEED)
    rows: list[dict[str, str]] = []
    for index, order_date in enumerate(_order_dates(rng, ORDER_COUNT), start=1):
        product, category, base_price = rng.choice(CATALOGUE)
        # Small price variation models promotions; prices stay positive.
        unit_price = round(base_price * rng.choice([1.0, 1.0, 1.0, 0.9, 0.85]), 2)
        quantity = rng.choices([1, 2, 3, 4, 5, 6], weights=[45, 25, 12, 8, 6, 4])[0]
        rows.append({
            "order_id": f"FF-{100000 + index}",
            "order_date": order_date.isoformat(),
            "product": product,
            "category": category,
            "quantity": str(quantity),
            "unit_price": f"{unit_price:.2f}",
            "revenue": f"{quantity * unit_price:.2f}",
            "region": rng.choices(REGIONS, weights=REGION_WEIGHTS)[0],
            "channel": rng.choices(CHANNELS, weights=CHANNEL_WEIGHTS)[0],
            "order_status": rng.choices(STATUSES, weights=STATUS_WEIGHTS)[0],
        })
    return rows


def inject_quality_issues(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rng = random.Random(SEED + 1)
    candidates = list(range(len(rows)))
    rng.shuffle(candidates)

    for position in candidates[:12]:
        rows[position]["region"] = ""
    for position in candidates[12:20]:
        region = rows[position]["region"] or "North"
        rows[position]["region"] = rng.choice([region.lower(), region.upper(), f" {region} "])
    for position, bad_value in zip(candidates[20:23], ["2025-13-01", "not recorded", "31/02/2025"]):
        rows[position]["order_date"] = bad_value
    for position in candidates[23:28]:
        rows[position]["channel"] = ""

    duplicates = [dict(rows[position]) for position in candidates[30:36]]
    for duplicate in duplicates:
        insert_at = rng.randrange(len(rows))
        rows.insert(insert_at, duplicate)
    return rows


def main() -> None:
    default_path = Path(__file__).resolve().parents[1] / "sample-data" / "flowforge-retail-sample.csv"
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = inject_quality_issues(build_rows())
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {output}")


if __name__ == "__main__":
    main()
