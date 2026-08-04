"""
QUALITY SOURCE — inspection records (structured).

One row per inspected unit: pass or fail, and if it failed, a defect code.
Joins back to machines and products by id. Feeds the "Quality" part of OEE and
the scrap/defect analysis in gold.

Usage:
    python generators/generate_quality.py --inspections 600
"""

import argparse
import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

from generators.reference import MACHINE_IDS, PRODUCT_IDS, DEFECT_CODES


def make_inspection(now):
    passed = random.random() > 0.06   # ~6% fail
    return {
        "inspection_id": str(uuid.uuid4()),
        "machine_id": random.choice(MACHINE_IDS),
        "product_id": random.choice(PRODUCT_IDS),
        "inspected_ts": now.isoformat(),
        "result": "PASS" if passed else "FAIL",
        # defect_code is null on a pass — a real nullable column silver must handle.
        "defect_code": None if passed else random.choice(DEFECT_CODES),
        "inspector": random.choice(["insp_A", "insp_B", "insp_C"]),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="data/landing/quality")
    p.add_argument("--inspections", type=int, default=600)
    p.add_argument("--files", type=int, default=3)
    args = p.parse_args()

    os.makedirs(args.out, exist_ok=True)
    per_file = args.inspections // args.files
    now = datetime.now(timezone.utc)
    total = 0
    for i in range(args.files):
        rows = []
        for _ in range(per_file):
            now = now - timedelta(seconds=random.randint(5, 30))
            rows.append(make_inspection(now))
        path = f"{args.out}/quality_{i:03d}.json"
        with open(path, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        total += len(rows)
        print(f"[file {i+1}/{args.files}] wrote {len(rows)} inspections")

    print(f"\nDone. {total} inspections in '{args.out}'.")


if __name__ == "__main__":
    main()
