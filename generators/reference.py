"""
Shared MASTER DATA for the factory.

All three sources (MES runs, sensor telemetry, quality checks) refer to the same
machines and products. In a real company this is the "master data" that lives in
the operational system and everything else joins back to. Defining it once here
keeps the three generators consistent — a sensor reading for machine M03 lines up
with an MES run on M03 and a quality check on M03.

MACHINES belong to production LINES and have a MAINTENANCE TIER. The tier is the
attribute we'll later track with SCD Type 2 (it can be upgraded over time, and we
want to remember what it was historically).

PRODUCTS carry an IDEAL CYCLE TIME — the theoretical fastest seconds to make one
unit. This is the backbone of the OEE "Performance" calculation later.
"""

# machine_id, name, production line, machine type, maintenance tier, install date
MACHINES = [
    {"machine_id": "M01", "machine_name": "CNC-Alpha",   "line": "LINE-A", "machine_type": "CNC",      "maintenance_tier": "standard", "install_date": "2019-03-12"},
    {"machine_id": "M02", "machine_name": "CNC-Beta",    "line": "LINE-A", "machine_type": "CNC",      "maintenance_tier": "standard", "install_date": "2019-05-20"},
    {"machine_id": "M03", "machine_name": "Press-Gamma", "line": "LINE-A", "machine_type": "Press",    "maintenance_tier": "premium",  "install_date": "2020-01-15"},
    {"machine_id": "M04", "machine_name": "Weld-Delta",  "line": "LINE-B", "machine_type": "Welder",   "maintenance_tier": "standard", "install_date": "2018-11-03"},
    {"machine_id": "M05", "machine_name": "Weld-Epsilon","line": "LINE-B", "machine_type": "Welder",   "maintenance_tier": "premium",  "install_date": "2021-06-28"},
    {"machine_id": "M06", "machine_name": "Assembler-Z", "line": "LINE-B", "machine_type": "Assembler","maintenance_tier": "standard", "install_date": "2020-09-09"},
]

# product_id, name, ideal cycle time (seconds to make ONE unit at theoretical max)
PRODUCTS = [
    {"product_id": "P100", "product_name": "Bracket-Std",   "ideal_cycle_time_sec": 12.0},
    {"product_id": "P200", "product_name": "Housing-Alloy",  "ideal_cycle_time_sec": 30.0},
    {"product_id": "P300", "product_name": "Gear-Precision", "ideal_cycle_time_sec": 45.0},
    {"product_id": "P400", "product_name": "Panel-Welded",   "ideal_cycle_time_sec": 20.0},
]

SHIFTS = ["morning", "afternoon", "night"]

# Defect codes a failed quality inspection might carry (NULL when the unit passes)
DEFECT_CODES = ["DENT", "CRACK", "MISALIGN", "BURR", "POROSITY", "TOLERANCE"]

MACHINE_IDS = [m["machine_id"] for m in MACHINES]
PRODUCT_IDS = [p["product_id"] for p in PRODUCTS]
