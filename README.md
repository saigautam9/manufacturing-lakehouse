# Manufacturing Lakehouse — Azure Databricks + Microsoft Fabric

An end-to-end medallion lakehouse for manufacturing analytics. Three factory data
sources (production runs, IoT sensor telemetry, quality inspections) flow through
bronze -> silver -> gold to serve the KPIs a plant manager actually uses: OEE,
downtime, and scrap rate.

Built local-first (runs anywhere on Parquet, no cloud account needed) and scaled
to millions of rows on Databricks with Delta + Unity Catalog.

## Two versions in this repo

This project follows a real engineering workflow: **prototype small locally, then
scale on the cluster.**

- **Local version** (`config/`, `generators/`, `pipeline/`) — clean, modular PySpark.
  Runs on a small dataset (6 machines, 5 days) for fast iteration and easy reading.
  Uses local Parquet so it runs with no cloud account.
- **Databricks version** (`databricks/lakehouse_notebook.ipynb`) — the same pipeline
  scaled to **50 machines, 90 days, ~2 million sensor rows**, running on Databricks
  Free Edition with **Delta + Unity Catalog**. Adds window-function analytics, time-
  series marts, a three-source join, incremental MERGE upserts, and SCD Type 2 via
  Delta MERGE.

The size difference is intentional: small data is ideal for local development;
big data belongs on the cluster that's built to process it efficiently.

## Data sources

| Source | Type | Origin |
|---|---|---|
| MES production runs | Structured | Synthetic — units, downtime, scrap per run |
| Sensor telemetry | Semi-structured (nested JSON) | Seeded from AI4I 2020 benchmark — real speed, torque, temperature, tool wear, failure flag |
| Quality inspections | Structured | Synthetic — pass/fail with defect codes |

All sources share master data (machines, products) and join on machine_id /
product_id in a star schema. MES and quality are synthetic so the sources join
cleanly; sensor telemetry is seeded from a public benchmark. No real production
data is used.

## Engineering highlights

- Medallion architecture: bronze (raw) -> silver (clean) -> gold (business KPIs).
- Quality gate + quarantine: bad rows routed to *_quarantine tables, never dropped.
- Semi-structured flattening of nested sensor JSON, robust to optional fields.
- SCD Type 2 machine dimension with full history (valid_from/valid_to/is_current);
  DataFrame logic locally, a single Delta MERGE on Databricks.
- OEE = Availability x Performance x Quality, per run then aggregated by machine and line.
- Window functions (Databricks): rolling 7-day OEE, running downtime, machine ranking per line.
- Time-series marts: daily and weekly OEE trends.
- Three-source join with a derived insight (tool-wear vs scrap correlation).
- Incremental MERGE upserts — the industry-standard pattern for applying changes.
- Portable Parquet <-> Delta via one env var (STORAGE_FORMAT).

## Tech stack

PySpark 4, Delta Lake, Unity Catalog, Databricks, Python, SQL (target platform:
Azure Databricks, Microsoft Fabric, Power BI).

## Run locally

Requires Python 3.10+ and Java 17.

    pip install -r requirements.txt

    python -m generators.generate_mes --days 5 --runs-per-day 12
    python -m generators.generate_quality --inspections 600
    python -m generators.generate_sensors --seed-file data/seed/ai4i2020.csv --readings 2000

    python -m pipeline.bronze_ingest
    python -m pipeline.silver_transform
    python -m pipeline.scd2_machine
    python -m pipeline.gold_marts

## Run on Databricks

See `databricks/lakehouse_notebook.ipynb`. Upload the AI4I CSV to a Unity Catalog
Volume, then run the cells top to bottom. Tables register in Unity Catalog under
workspace.manufacturing and can be served to Power BI.

## Project layout

    config/       settings + spark session builder
    generators/   reference master data, MES, sensors (AI4I seed), quality, sim helper
    pipeline/     bronze_ingest, silver_transform, scd2_machine, gold_marts
    databricks/   scaled Databricks notebook (2M rows, Delta, Unity Catalog)

## Attribution

Sensor data seeded from the AI4I 2020 Predictive Maintenance Dataset by Stephan
Matzka (UCI Machine Learning Repository), licensed CC BY-NC-SA 4.0. A synthetic
benchmark dataset; used here for non-commercial, educational purposes.
