"""
SENSOR SOURCE — semi-structured IoT telemetry.

Two modes:
  * SEEDED (recommended): pass --seed-file pointing at the real UCI "AI4I 2020
    Predictive Maintenance" CSV. We map its REAL columns (rotational speed,
    torque, process temperature, tool wear, machine-failure flag) into our
    telemetry shape. Credible, real distributions.
  * SYNTHETIC (fallback): no seed file -> fully invented readings, so the repo
    always runs even without the download.

Honest note for interviews: rotational_speed, torque, temperature, tool_wear and
the failure flag are REAL (from AI4I). AI4I has no vibration sensor, so vibration
is synthesized and labelled as such.

Each record stays nested (a "readings" object) = semi-structured, so silver still
has flattening work.

Usage:
    # real-seeded (after downloading ai4i2020.csv):
    python -m generators.generate_sensors --seed-file data/seed/ai4i2020.csv --readings 2000
    # fully synthetic:
    python -m generators.generate_sensors --readings 400
"""

import argparse
import csv
import json
import os
import random
from datetime import datetime, timedelta, timezone

from generators.reference import MACHINE_IDS


# ---- helpers ---------------------------------------------------------------

def _num(row, *names):
    """Get the first present column by name, tolerant of header spacing."""
    for n in names:
        for key in row:
            if key.strip().lower() == n.strip().lower():
                v = row[key].strip()
                return v if v != "" else None
    return None


def make_reading_synthetic(now):
    readings = {
        "temperature_c": round(random.gauss(65, 8), 1),
        "vibration_mm_s": round(abs(random.gauss(2.5, 1.0)), 2),
        "rotational_speed_rpm": random.randint(1200, 3000),
        "torque_nm": round(random.gauss(40, 6), 1),
    }
    return {
        "machine_id": random.choice(MACHINE_IDS),
        "reading_ts": now.isoformat(),
        "firmware": random.choice(["v1.2", "v1.3", "v2.0"]),
        "source": "synthetic",
        "readings": readings,
        "machine_failure": False,
    }


def make_reading_from_ai4i(csv_row, now):
    """Map one real AI4I row -> our telemetry record."""
    proc_k = _num(csv_row, "Process temperature [K]", "Process temperature")
    speed  = _num(csv_row, "Rotational speed [rpm]", "Rotational speed")
    torque = _num(csv_row, "Torque [Nm]", "Torque")
    wear   = _num(csv_row, "Tool wear [min]", "Tool wear")
    fail   = _num(csv_row, "Machine failure", "Target")

    readings = {
        # REAL: Kelvin -> Celsius
        "temperature_c": round(float(proc_k) - 273.15, 1) if proc_k else None,
        # SYNTHESIZED: AI4I has no vibration sensor
        "vibration_mm_s": round(abs(random.gauss(2.5, 1.0)), 2),
        # REAL:
        "rotational_speed_rpm": int(float(speed)) if speed else None,
        "torque_nm": round(float(torque), 1) if torque else None,
        "tool_wear_min": int(float(wear)) if wear else None,   # REAL predictive signal
    }
    return {
        "machine_id": random.choice(MACHINE_IDS),   # assign to one of our machines
        "reading_ts": now.isoformat(),
        "firmware": random.choice(["v1.2", "v1.3", "v2.0"]),
        "source": "ai4i-seed",
        "readings": readings,
        "machine_failure": bool(int(fail)) if fail else False,
    }


def load_ai4i(path, limit):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    random.shuffle(rows)
    return rows[:limit] if limit else rows


# ---- main ------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="data/landing/sensors")
    p.add_argument("--readings", type=int, default=400)
    p.add_argument("--files", type=int, default=4)
    p.add_argument("--seed-file", default=None,
                   help="path to real AI4I 2020 CSV; omit for fully synthetic")
    args = p.parse_args()

    os.makedirs(args.out, exist_ok=True)
    now = datetime.now(timezone.utc)

    seed_rows = load_ai4i(args.seed_file, args.readings) if args.seed_file else None
    n = len(seed_rows) if seed_rows is not None else args.readings
    mode = "AI4I-seeded (real)" if seed_rows is not None else "synthetic"
    per_file = max(1, n // args.files)

    total = 0
    for i in range(args.files):
        rows = []
        for j in range(per_file):
            now = now - timedelta(seconds=random.randint(1, 20))
            if seed_rows is not None:
                idx = i * per_file + j
                if idx >= len(seed_rows):
                    break
                rec = make_reading_from_ai4i(seed_rows[idx], now)
            else:
                rec = make_reading_synthetic(now)
            # ~3% sensor glitch: drop a reading field -> null downstream
            if random.random() < 0.03 and rec["readings"]:
                k = random.choice(list(rec["readings"].keys()))
                del rec["readings"][k]
            rows.append(rec)
        if not rows:
            break
        path = f"{args.out}/sensors_{i:03d}.json"
        with open(path, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        total += len(rows)
        print(f"[file {i+1}/{args.files}] wrote {len(rows)} readings")

    print(f"\nDone ({mode}). {total} sensor readings in '{args.out}'.")


if __name__ == "__main__":
    main()
