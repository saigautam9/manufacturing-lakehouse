# Manufacturing Analytics Lakehouse — Databricks + Microsoft Fabric

An end-to-end data platform for manufacturing analytics. Raw factory data flows through
a medallion lakehouse on **Azure Databricks**, gains a **machine-learning failure-prediction**
layer, and is served through **Microsoft Fabric** to a **Power BI** dashboard. It computes the
KPIs a plant actually runs on — OEE, downtime by loss category, scrap, and predictive-
maintenance risk.

**Stack:** Azure Databricks · Delta Lake · Unity Catalog · PySpark · MLflow · Microsoft Fabric (OneLake) · Power BI · Python · SQL

---

## Capability → where it's demonstrated

| Capability | In this project |
|---|---|
| Azure Databricks pipelines | Full bronze → silver → gold medallion, run on Databricks |
| Delta Lake | All tables are managed Delta tables (ACID, schema enforcement, MERGE, time travel) |
| Unity Catalog governance | Tables registered under `workspace.manufacturing` (catalog / schema / table namespace) |
| PySpark ETL/ELT | Ingestion, cleaning, joins, window functions, aggregations |
| Microsoft Fabric | Gold layer loaded into a Fabric Lakehouse (OneLake) |
| Power BI | 6-visual Direct Lake dashboard on the Fabric Lakehouse |
| Machine learning | Random Forest failure prediction, MLflow-tracked |
| Structured + semi-structured data | Flat MES tables + nested JSON sensor telemetry |

---

## Architecture

```
 MES runs          Sensor telemetry (AI4I)      Quality inspections
 (structured)      (semi-structured JSON)       (structured)
        \                  |                            /
                      BRONZE   (raw Delta + lineage)
                          |
                      SILVER   (cleaned, quality-gated, per-run OEE)
                          |
          SCD Type 2 -----|   machine dimension history (Delta MERGE)
                          |
                       GOLD    (OEE, Six Big Losses, downtime Pareto, machine health)
                          |
              +-----------+------------+
       ML failure-risk model       Microsoft Fabric Lakehouse (OneLake)
       (Random Forest, MLflow)             |
                                  Power BI Direct Lake dashboard
```

---

## Engineering highlights

- **Medallion architecture** (bronze / silver / gold) on Databricks with Delta Lake.
- **Six Big Losses taxonomy** — ~28k event-level downtime records categorized by loss type
  (breakdown, changeover, minor stop, reduced speed, material starvation, planned
  maintenance), powering a downtime Pareto and a loss-category breakdown — the analyses
  real plants use to prioritize improvements.
- **OEE = Availability × Performance × Quality**, computed per production run and aggregated
  by machine, line, and shift, with benchmark-grounded realistic distributions.
- **Window functions** — rolling 7-day OEE, running downtime, machine ranking per line.
- **SCD Type 2** machine dimension with full history tracking via Delta MERGE.
- **Incremental MERGE** upserts on the fact tables.
- **Quality gates + quarantine** — invalid rows are routed aside, never silently dropped.
- **Semi-structured handling** — nested JSON sensor telemetry flattened dynamically.
- **Scaled** to 50 machines x 90 days x 3 shifts ~ 2M sensor rows on Databricks.

---

## Machine learning — predictive maintenance

- **Random Forest** trained on the AI4I 2020 sensor benchmark to predict machine failure.
- **Regularized** (`max_depth=6`) after detecting overfitting on a deeper model.
- **Validated** — 5-fold cross-validation AUC ~ 0.93; checked for data leakage and duplicate
  rows; reports ROC-AUC and recall rather than accuracy (the data is 3.4%-imbalanced, so
  accuracy alone is misleading).
- **Tracked in MLflow** (Experiments tab), with feature importance (tool wear, torque,
  rotational speed as top predictors).
- Feeds a **condition-based failure-risk index** that ranks machines by maintenance priority
  (age, OEE, and failure history).

---

## Serving — Microsoft Fabric + Power BI

Gold tables are loaded into a **Fabric Lakehouse (OneLake)** as Delta tables and surfaced
through a **Power BI Direct Lake** dashboard with 6 visuals:

1. Overall OEE KPI
2. Top-10 at-risk machines (predictive-maintenance ranking)
3. Average OEE by production line
4. OEE vs failure-risk scatter (shows the inverse relationship)
5. Downtime Pareto by reason
6. Downtime by loss category (Availability / Performance / Quality)

---

## Repo layout

```
config/        settings + Spark session builder (local version)
generators/    MES, sensor (AI4I seed), and quality data generators
pipeline/      bronze / silver / scd2 / gold (local modular version)
databricks/    lakehouse_notebook.ipynb -- scaled Databricks pipeline + ML
```

---

## Data note

MES and quality data are **synthetic**, grounded in published OEE benchmarks (world-class 85%,
discrete-manufacturing average 55-65%, Six Big Losses framework). Sensor telemetry is seeded
from the AI4I 2020 Predictive Maintenance benchmark. **No real production data is used.**

## Attribution

AI4I 2020 Predictive Maintenance Dataset by Stephan Matzka (UCI Machine Learning Repository),
CC BY-NC-SA 4.0 — a synthetic benchmark, used here for non-commercial, educational purposes.
