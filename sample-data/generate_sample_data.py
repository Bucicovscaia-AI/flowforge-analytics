"""Generate the synthetic (fabricated) sample datasets used by FlowForge.

Run from the repository root:

    python sample-data/generate_sample_data.py

The random generator is seeded, so the same files are produced every time.
No real business, customer or transaction is described by these files.

Two datasets are written:

* ``retail_sales_2026_synthetic.csv``: about 1,150 order lines from January
  to June 2026, with deliberate data-quality problems injected so the
  cleaning rules have something real to find (duplicate rows, blank cells,
  unparseable dates, negative quantities, prices with currency symbols and
  inconsistent capitalisation).
* ``web_orders_minimal_synthetic.csv``: a smaller file with only the four
  required columns. It shows how the app reports KPIs it cannot calculate
  because the needed columns are missing.
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
SEED = 20261027

PRODUCTS = {
    "Electronics": [("Wireless Earbuds", 59.99), ("Smart Speaker", 89.0), ("USB-C Charger", 19.5), ("4K Monitor", 179.0)],
    "Home & Garden": [("Ceramic Planter", 24.0), ("LED Desk Lamp", 34.99), ("Cotton Throw", 29.5), ("Herb Seed Kit", 12.0)],
    "Clothing": [("Rain Jacket", 74.0), ("Merino Socks", 14.5), ("Canvas Trainers", 49.99), ("Wool Beanie", 18.0)],
    "Sports": [("Yoga Mat", 27.0), ("Water Bottle", 15.99), ("Resistance Bands", 21.5)],
    "Books": [("Data Analysis Handbook", 32.0), ("Travel Journal", 11.99), ("Cookbook Classics", 22.5)],
}
CATEGORY_WEIGHTS = {"Electronics": 0.2, "Home & Garden": 0.25, "Clothing": 0.25, "Sports": 0.17, "Books": 0.13}
REGIONS = {"North": 0.29, "East": 0.26, "West": 0.24, "South": 0.21}
CHANNELS = {"Online": 0.58, "In-store": 0.30, "Phone": 0.12}
CUSTOMER_TYPES = {"Returning": 0.55, "New": 0.35, "Business": 0.10}

# Orders per day rise gently through the half-year, with a dip in April,
# so the trend chart has a shape worth describing.
MONTH_FACTOR = {1: 0.85, 2: 0.9, 3: 1.0, 4: 0.92, 5: 1.08, 6: 1.18}

HEADER = ["order_id", "order_date", "product", "product_category", "region", "channel", "customer_type", "quantity", "unit_price"]


def pick(rng: random.Random, weights: dict[str, float]) -> str:
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def build_clean_lines(rng: random.Random) -> list[dict[str, str]]:
    lines: list[dict[str, str]] = []
    order_number = 10001
    day = date(2026, 1, 1)
    while day <= date(2026, 6, 30):
        orders_today = max(1, round(rng.gauss(4.6 * MONTH_FACTOR[day.month], 1.4)))
        for _ in range(orders_today):
            order_id = f"ORD-{order_number}"
            order_number += 1
            region = pick(rng, REGIONS)
            channel = pick(rng, CHANNELS)
            customer = pick(rng, CUSTOMER_TYPES)
            # One to three different products per order: an order can have
            # several lines, but never the same product twice.
            chosen: set[str] = set()
            for _ in range(rng.choices([1, 2, 3], weights=[0.7, 0.22, 0.08])[0]):
                category = pick(rng, CATEGORY_WEIGHTS)
                product, price = rng.choice(PRODUCTS[category])
                if product in chosen:
                    continue
                chosen.add(product)
                quantity = rng.choices([1, 2, 3, 4, 5], weights=[0.55, 0.24, 0.11, 0.06, 0.04])[0]
                if customer == "Business":
                    quantity += rng.randint(2, 8)
                lines.append(
                    {
                        "order_id": order_id,
                        "order_date": day.isoformat(),
                        "product": product,
                        "product_category": category,
                        "region": region,
                        "channel": channel,
                        "customer_type": customer,
                        "quantity": str(quantity),
                        "unit_price": f"{price:.2f}",
                    }
                )
        day += timedelta(days=1)
    return lines


def inject_problems(rng: random.Random, lines: list[dict[str, str]]) -> list[dict[str, str]]:
    """Add realistic data-quality issues. Counts are fixed so tests and
    documentation can rely on them."""
    rows = [dict(line) for line in lines]
    indices = rng.sample(range(len(rows)), 60)
    blanks_type, blanks_channel = indices[0:12], indices[12:19]
    bad_dates, negative_qty, missing_price = indices[19:24], indices[24:28], indices[28:31]
    currency_price, lower_region, padded = indices[31:41], indices[41:51], indices[51:60]

    for i in blanks_type:
        rows[i]["customer_type"] = ""
    for i in blanks_channel:
        rows[i]["channel"] = "N/A"
    for i, bad in zip(bad_dates, ["2026-02-30", "not recorded", "31/13/2026", "2026-13-01", "TBC"]):
        rows[i]["order_date"] = bad
    for i in negative_qty:
        rows[i]["quantity"] = str(-int(rows[i]["quantity"]))
    for i in missing_price:
        rows[i]["unit_price"] = ""
    for i in currency_price:
        rows[i]["unit_price"] = f"£{rows[i]['unit_price']}"
    for i in lower_region:
        rows[i]["region"] = rows[i]["region"].lower()
    for i in padded:
        rows[i]["product"] = f"  {rows[i]['product']} "

    # Exact duplicate rows, as if an export had been appended twice.
    duplicates = [dict(rows[i]) for i in rng.sample(range(len(rows)), 15)]
    for dup in duplicates:
        rows.insert(rng.randrange(len(rows)), dup)
    return rows


def write_csv(path: Path, rows: list[dict[str, str]], header: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {path.name}")


def main() -> None:
    rng = random.Random(SEED)
    clean = build_clean_lines(rng)
    write_csv(OUT_DIR / "retail_sales_2026_synthetic.csv", inject_problems(rng, clean), HEADER)

    minimal_rng = random.Random(SEED + 1)
    minimal = [line for line in build_clean_lines(minimal_rng) if line["order_date"] < "2026-04-01"]
    write_csv(OUT_DIR / "web_orders_minimal_synthetic.csv", minimal, ["order_id", "order_date", "quantity", "unit_price"])


if __name__ == "__main__":
    main()
