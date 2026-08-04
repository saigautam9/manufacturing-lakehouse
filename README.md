# Manufacturing Lakehouse — Azure Databricks + Microsoft Fabric

An end-to-end medallion lakehouse for manufacturing analytics. Three factory data
sources (production runs, IoT sensor telemetry, quality inspections) flow through
bronze -> silver -> gold to serve the KPIs a plant manager actually uses: OEE,
downtime, and scrap rate.

Built local-first (runs anywhere on Parquet, no cloud account needed) and designed
to move to Azure Databricks + Delta by flipping a single config switch, where it
also gains Unity Catalog governance and Microsoft Fabric + Power BI serving.

## Data sources

| Source | Type | Origin |
|---|---|---|
| MES production runs | Structured | Synthetic — units, downtime, scrap per run |
| Sensor telemetry | Semi-structured (nested JSON) | Seeded from AI4I 2020 benchmark — real speed, torque, temperature, tool wear, failure flag |
| Quality inspections | Structured | Synthetic — pass/fail with defect codes |

All three share master data (6 machines, 4 products) and join on machine_id /
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
- Portable Parquet <-> Delta via one env var (STORAGE_FORMAT).

## Tech stack

PySpark 4, Delta Lake, Python, SQL (target: Azure Databricks, Unity Catalog,
Microsoft Fabric, Power BI).

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

## Run on Azure Databricks

Set STORAGE_FORMAT=delta, point layer paths at ADLS Gen2, and Auto Loader replaces
the batch reader in bronze. Gold tables register in Unity Catalog and surface to
Power BI via a Microsoft Fabric OneLake shortcut.

## Project layout

    config/       settings + spark session builder
    generators/   reference master data, MES, sensors (AI4I seed), quality, sim helper
    pipeline/     bronze_ingest, silver_transform, scd2_machine, gold_marts

## Attribution

Sensor data seeded from the AI4I 2020 Predictive Maintenance Dataset by Stephan
Matzka (UCI Machine Learning Repository), licensed CC BY-NC-SA 4.0. A synthetic
benchmark dataset; used here for non-commercial, educational purposes.
