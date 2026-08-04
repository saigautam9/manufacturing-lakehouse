"""
Central settings for the manufacturing lakehouse.

Everything that differs between "my laptop" and "Azure Databricks" lives here so
the pipeline code never hard-codes where it runs.

STORAGE_FORMAT is the one switch that matters:
  - "parquet" -> runs anywhere, no setup (local dev).
  - "delta"   -> on Azure Databricks: adds ACID, time travel, MERGE, and is what
                 Unity Catalog + Fabric OneLake read.

On Databricks the paths would point at ADLS Gen2 (abfss://...) instead of local
folders, but nothing else changes.
"""

import os

# --- landing: raw drops from each of the three sources -----------------------
LANDING_DIR   = os.environ.get("LANDING_DIR", "data/landing")
MES_LANDING   = f"{LANDING_DIR}/mes"        # production runs + reference dims
SENSOR_LANDING = f"{LANDING_DIR}/sensors"   # semi-structured telemetry json
QUALITY_LANDING = f"{LANDING_DIR}/quality"  # inspection records

# --- medallion layers --------------------------------------------------------
BRONZE_PATH = os.environ.get("BRONZE_PATH", "data/bronze")
SILVER_PATH = os.environ.get("SILVER_PATH", "data/silver")
GOLD_PATH   = os.environ.get("GOLD_PATH",   "data/gold")

CHECKPOINT_DIR = os.environ.get("CHECKPOINT_DIR", "data/_checkpoints")

# --- the laptop <-> Databricks switch ---------------------------------------
STORAGE_FORMAT = os.environ.get("STORAGE_FORMAT", "parquet")  # "delta" on Databricks
