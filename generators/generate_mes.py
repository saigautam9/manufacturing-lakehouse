"""
MES SOURCE (Manufacturing Execution System) — the operational database.

Emits three things:
  1. machines.json  — the machine dimension (master data), written once.
  2. products.json  — the product dimension (master data), written once.
  3. runs_*.json    — production RUN facts: one row per machine/product/shift run.

The run fact carries everything needed to compute OEE downstream:
  planned_production_min, downtime_min, total_units, good_units.

This mimics a Fivetran-style pull of tables from a factory's operational DB.

Usage:
    python generators/generate_mes.py --days 5 --runs-per-day 12
"""

import argparse
import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

from generators.reference import (MACHINES, PRODUCTS, SHIFTS,
                                  MACHINE_IDS, PRODUCT_IDS)

PRODUCT_IDEAL = {p["product_id"]: p["ideal_cycle_time_sec"] for p in PRODUCTS}


def _write(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def write_dimensions(out_dir):
    """Master data — written once, like a full-table sync of the dim tables."""
    _write(f"{out_dir}/machines.json", MACHINES)
    _write(f"{out_dir}/products.json", PRODUCTS)


def make_run(run_date, machine_id, product_id, shift):
    planned = 480  # an 8-hour shift in minutes
    # Unplanned downtime eats into availability. Premium-tier machines break less.
    tier = next(m["maintenance_tier"] for m in MACHINES if m["machine_id"] == machine_id)
    max_down = 60 if tier == "premium" else 110
    downtime = random.randint(5, max_down)
    run_time_min = planned - downtime

    ideal_sec = PRODUCT_IDEAL[product_id]
    # Theoretical max units if we ran at ideal speed for the whole run_time.
    theoretical = (run_time_min * 60) / ideal_sec
    # Real performance is 70-98% of theoretical.
    total_units = int(theoretical * random.uniform(0.70, 0.98))
    # Scrap rate 1-9%.
    scrapped = int(total_units * random.uniform(0.01, 0.09))
    good_units = total_units - scrapped

    row = {
        "run_id": str(uuid.uuid4()),
        "run_date": run_date,
        "machine_id": machine_id,
        "product_id": product_id,
        "shift": shift,
        "planned_production_min": planned,
        "downtime_min": downtime,
        "total_units": total_units,
        "good_units": good_units,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }

    # Inject a little dirtiness for silver's quality gate to catch:
    if random.random() < 0.04:
        row["product_id"] = None            # missing FK -> should quarantine
    if random.random() < 0.03:
        row["total_units"] = -1             # impossible value -> should quarantine
    return row


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="data/landing/mes")
    p.add_argument("--days", type=int, default=5)
    p.add_argument("--runs-per-day", type=int, default=12)
    args = p.parse_args()

    write_dimensions(args.out)

    start = datetime.now(timezone.utc).date() - timedelta(days=args.days - 1)
    total = 0
    for d in range(args.days):
        run_date = (start + timedelta(days=d)).isoformat()
        rows = []
        for _ in range(args.runs_per_day):
            rows.append(make_run(
                run_date,
                random.choice(MACHINE_IDS),
                random.choice(PRODUCT_IDS),
                random.choice(SHIFTS),
            ))
        _write(f"{args.out}/runs_{run_date}.json", rows)
        total += len(rows)
        print(f"[{run_date}] wrote {len(rows)} runs")

    print(f"\nDone. dims + {total} runs in '{args.out}'.")


if __name__ == "__main__":
    main()
