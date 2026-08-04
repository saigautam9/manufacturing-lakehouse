"""
Simulate a change to a machine's attribute, so we can demonstrate SCD Type 2.

Edits the landing machines.json (e.g. upgrade M01 to premium). After running this,
re-run bronze + scd2_machine and you'll see the machine gain a second (historical)
row: the old version closed, the new version current.

Usage:
    python -m generators.simulate_machine_change --machine M01 --tier premium
"""

import argparse
import json

MACHINES_FILE = "data/landing/mes/machines.json"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--machine", default="M01")
    p.add_argument("--tier", default="premium", help="new maintenance_tier")
    p.add_argument("--line", default=None, help="optionally change the line too")
    p.add_argument("--file", default=MACHINES_FILE)
    args = p.parse_args()

    with open(args.file) as f:
        machines = [json.loads(line) for line in f if line.strip()]

    changed = False
    for m in machines:
        if m["machine_id"] == args.machine:
            old = m.get("maintenance_tier")
            m["maintenance_tier"] = args.tier
            if args.line:
                m["line"] = args.line
            changed = True
            print(f"{args.machine}: maintenance_tier {old} -> {args.tier}")

    if not changed:
        print(f"Machine {args.machine} not found.")
        return

    with open(args.file, "w") as f:
        for m in machines:
            f.write(json.dumps(m) + "\n")
    print(f"Updated {args.file}. Now re-run bronze + scd2_machine to see history.")


if __name__ == "__main__":
    main()
