"""
SILVER LAYER — clean, flatten, and quality-gate each source.

Bronze kept everything raw (including the nested sensor JSON and a few bad rows).
Silver makes each source trustworthy and query-ready:

  * mes_runs : validate the run facts; quarantine broken rows (null product FK,
               impossible unit counts).
  * sensors  : FLATTEN the nested "readings" struct into plain columns, cast the
               timestamp, quarantine readings with missing core signals.
  * quality  : light clean; keep defect_code null-on-pass (a valid null).

Bad rows are QUARANTINED (routed to a *_quarantine table), never silently dropped.

Batch/ELT style (spark.read), consistent with bronze. The machine dimension gets
its own SCD Type 2 job (built separately) because that logic is richer.
"""

from pyspark.sql import functions as F

from config.spark_session import get_spark
from config.settings import BRONZE_PATH, SILVER_PATH, STORAGE_FORMAT


def _split_write(df, valid_expr, name):
    """Split a DataFrame into valid/quarantine by a boolean expression and write both."""
    df = df.withColumn("is_valid", valid_expr)
    good = df.filter("is_valid").drop("is_valid")
    bad = df.filter("NOT is_valid")
    good.write.format(STORAGE_FORMAT).mode("overwrite").save(f"{SILVER_PATH}/{name}")
    bad.write.format(STORAGE_FORMAT).mode("overwrite").save(f"{SILVER_PATH}/{name}_quarantine")
    print(f"  {name:<16} valid={good.count():>5}  quarantine={bad.count():>4}")


def clean_mes_runs(spark):
    df = spark.read.format(STORAGE_FORMAT).load(f"{BRONZE_PATH}/mes_runs")
    # A run is valid only if its keys resolve and its unit counts make sense.
    valid = (
        F.col("machine_id").isNotNull()
        & F.col("product_id").isNotNull()          # catches the injected null FK
        & (F.col("total_units") > 0)               # catches the injected -1
        & (F.col("good_units") >= 0)
        & (F.col("good_units") <= F.col("total_units"))
    )
    _split_write(df, valid, "mes_runs")


def flatten_sensors(spark):
    df = spark.read.format(STORAGE_FORMAT).load(f"{BRONZE_PATH}/sensors")

    # FLATTEN: pull every field out of the nested "readings" struct into its own
    # top-level column. We read the struct's field names dynamically so this works
    # whether the data was AI4I-seeded (has tool_wear_min) or fully synthetic.
    reading_fields = [f.name for f in df.schema["readings"].dataType.fields]
    base_cols = [c for c in df.columns if c != "readings"]
    flat = df.select(
        *base_cols,
        *[F.col(f"readings.{name}").alias(name) for name in reading_fields],
    )

    # Cast the timestamp string to a real timestamp.
    flat = flat.withColumn("reading_ts", F.to_timestamp("reading_ts"))

    # A reading is valid if it identifies a machine and carries the core signals.
    valid = (
        F.col("machine_id").isNotNull()
        & F.col("rotational_speed_rpm").isNotNull()   # dropped-field rows fail here
        & F.col("torque_nm").isNotNull()
    )
    _split_write(flat, valid, "sensors")


def clean_quality(spark):
    df = spark.read.format(STORAGE_FORMAT).load(f"{BRONZE_PATH}/quality")
    df = (df
          .withColumn("inspected_ts", F.to_timestamp("inspected_ts"))
          .withColumn("result", F.upper(F.trim(F.col("result")))))   # standardize
    # defect_code is legitimately null on a PASS, so we don't gate on it.
    valid = (
        F.col("inspection_id").isNotNull()
        & F.col("machine_id").isNotNull()
        & F.col("result").isin("PASS", "FAIL")
    )
    _split_write(df, valid, "quality")


def run():
    spark = get_spark("silver_transform")
    spark.sparkContext.setLogLevel("WARN")
    print("Building silver (valid vs quarantine):")
    clean_mes_runs(spark)
    flatten_sensors(spark)
    clean_quality(spark)
    print("Silver transform complete.")
    spark.stop()


if __name__ == "__main__":
    run()
