"""
BRONZE LAYER — land all sources raw, one table each.

Project 1 was a live stream; this project is BATCH/INCREMENTAL ELT, which suits
manufacturing (data arrives in periodic loads, not a constant firehose). So here
we use spark.read (batch), not readStream.

We land FIVE raw tables:
    dim_machines, dim_products  <- the MES dimensions (master data)
    mes_runs                    <- the MES production-run facts
    sensors                     <- semi-structured telemetry (kept nested for now)
    quality                     <- inspection records

Bronze rule (same as always): copy raw, change nothing. We only add two lineage
stamps: when we ingested, and which file each row came from.

On Databricks you'd swap spark.read.json(path) for Auto Loader
(spark.readStream.format("cloudFiles")) to load new files incrementally.
"""

from pyspark.sql import functions as F

from config.spark_session import get_spark
from config.settings import (MES_LANDING, SENSOR_LANDING, QUALITY_LANDING,
                             BRONZE_PATH, STORAGE_FORMAT)


def ingest(spark, source_glob, bronze_table, multiline=False, glob_filter=None):
    """Read a source's JSON, stamp lineage, write one raw bronze table."""
    reader = spark.read
    if multiline:
        reader = reader.option("multiLine", "true")
    # Point Spark at a real directory and filter files with pathGlobFilter, rather
    # than passing a wildcard path. A wildcard path isn't a real folder, so Spark's
    # "is this a streaming sink?" probe throws a noisy (harmless) FileNotFound. Using
    # the directory + pathGlobFilter avoids that entirely.
    if glob_filter:
        reader = reader.option("pathGlobFilter", glob_filter)

    df = reader.json(source_glob)

    # Two lineage columns — invaluable when debugging three layers downstream.
    df = (df
          .withColumn("_ingest_time", F.current_timestamp())
          .withColumn("_source_file", F.input_file_name()))

    out = f"{BRONZE_PATH}/{bronze_table}"
    df.write.format(STORAGE_FORMAT).mode("overwrite").save(out)
    print(f"  {bronze_table:<14} rows={df.count():>5}  -> {out}")
    return df


def run():
    spark = get_spark("bronze_ingest")
    spark.sparkContext.setLogLevel("WARN")

    print("Ingesting raw sources into bronze:")
    # MES dimensions (small master-data tables, read individually).
    ingest(spark, f"{MES_LANDING}/machines.json", "dim_machines")
    ingest(spark, f"{MES_LANDING}/products.json", "dim_products")
    # MES facts — the run files live alongside the dims, so filter to runs_*.json.
    ingest(spark, MES_LANDING, "mes_runs", glob_filter="runs_*.json")
    # Semi-structured + structured event sources (whole directory).
    ingest(spark, SENSOR_LANDING, "sensors")
    ingest(spark, QUALITY_LANDING, "quality")

    print("Bronze ingest complete.")
    spark.stop()


if __name__ == "__main__":
    run()
