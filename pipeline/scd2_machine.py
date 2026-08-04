"""
SCD TYPE 2 — machine dimension with history.

A machine's attributes (its line, its maintenance tier) can change over time.
SCD Type 2 keeps the FULL history instead of overwriting: when a tracked attribute
changes, we close the old record (set valid_to, is_current=false) and insert a new
record (valid_from=today, is_current=true).

Result: one machine can have several rows — one per "era" of its life.

Local (Parquet) note: we express the SCD2 logic with plain DataFrame operations so
it runs anywhere. On Databricks you'd do the same thing with a single Delta MERGE:

    MERGE INTO dim_machine_scd2 t
    USING updates u ON t.machine_id = u.machine_id AND t.is_current = true
    WHEN MATCHED AND (t.maintenance_tier <> u.maintenance_tier OR t.line <> u.line)
         THEN UPDATE SET t.is_current = false, t.valid_to = current_date()
    WHEN NOT MATCHED THEN INSERT (...);

...plus an insert of the new current rows. The DataFrame version below does exactly
that, step by step, so you can see the mechanics.
"""

import os
import shutil

from pyspark.sql import functions as F

from config.spark_session import get_spark
from config.settings import BRONZE_PATH, SILVER_PATH, STORAGE_FORMAT

# The business columns that live in the dimension.
DIM_COLS = ["machine_id", "machine_name", "line", "machine_type",
            "maintenance_tier", "install_date"]
# The attributes we TRACK for changes. A change in any of these opens a new version.
TRACKED = ["line", "maintenance_tier"]

SCD2_PATH = f"{SILVER_PATH}/dim_machine_scd2"


def _add_scd_cols(df):
    """Stamp a snapshot as brand-new current records."""
    return (df
            .withColumn("valid_from", F.current_date())
            .withColumn("valid_to", F.lit(None).cast("date"))
            .withColumn("is_current", F.lit(True)))


def run():
    spark = get_spark("scd2_machine")
    spark.sparkContext.setLogLevel("WARN")

    # The incoming snapshot = the latest machine dimension from bronze.
    incoming = spark.read.format(STORAGE_FORMAT).load(f"{BRONZE_PATH}/dim_machines").select(*DIM_COLS)

    # FIRST RUN: no history yet -> initialize every machine as a current record.
    if not os.path.exists(SCD2_PATH):
        _add_scd_cols(incoming).write.format(STORAGE_FORMAT).mode("overwrite").save(SCD2_PATH)
        print(f"Initialized SCD2 with {incoming.count()} current machine records.")
        spark.stop()
        return

    existing = spark.read.format(STORAGE_FORMAT).load(SCD2_PATH)
    current = existing.filter("is_current")          # the live versions
    history = existing.filter("NOT is_current")       # already-closed versions (untouched)

    # Compare incoming to the current versions to classify each machine.
    current_keyed = current.select(
        "machine_id",
        *[F.col(c).alias(f"cur_{c}") for c in TRACKED],
    )
    j = incoming.join(current_keyed, "machine_id", "left")

    matched = F.col("cur_maintenance_tier").isNotNull()
    is_changed = matched & (
        (F.col("line") != F.col("cur_line"))
        | (F.col("maintenance_tier") != F.col("cur_maintenance_tier"))
    )
    is_new = ~matched

    changed_ids = j.filter(is_changed).select("machine_id")

    # 1) NEW CURRENT rows: brand-new machines + changed machines (their new version).
    new_current = _add_scd_cols(
        j.filter(is_new | is_changed).select(*DIM_COLS)
    )

    # 2) EXPIRE the old current rows whose machine changed: close them out.
    to_expire = (current.join(changed_ids, "machine_id", "inner")
                 .withColumn("valid_to", F.current_date())
                 .withColumn("is_current", F.lit(False)))

    # 3) KEEP the current rows that did NOT change, as-is.
    to_keep = current.join(changed_ids, "machine_id", "left_anti")

    # Compute the summary counts NOW, while the source files still exist. If we did
    # this after the file swap below, Spark's lazy re-read would hit deleted files.
    n_changed = changed_ids.count()
    n_new = j.filter(is_new).count()

    # Final table = old history + kept current + newly-expired + new current.
    result = (history
              .unionByName(to_keep)
              .unionByName(to_expire)
              .unionByName(new_current))

    # Write to a temp path, then swap, so we never read and write the same path at once.
    tmp = SCD2_PATH + "_tmp"
    result.write.format(STORAGE_FORMAT).mode("overwrite").save(tmp)
    shutil.rmtree(SCD2_PATH)
    shutil.move(tmp, SCD2_PATH)

    print(f"SCD2 updated: {n_changed} changed (new version added), {n_new} brand-new.")
    spark.stop()


if __name__ == "__main__":
    run()
