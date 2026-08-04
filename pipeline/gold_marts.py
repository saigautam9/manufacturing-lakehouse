"""
GOLD LAYER — business KPIs. This is where the three sources finally join.

We produce three marts a plant manager actually looks at:

  1. gold_oee_by_machine  — OEE (Availability x Performance x Quality) per machine,
                            with total downtime and units. The headline factory KPI.
  2. gold_oee_by_line     — the same rolled up to production line.
  3. gold_machine_health  — the 3-source join: production OEE + sensor health
                            (avg/max temperature, failures, tool wear) + quality
                            fail rate, all keyed on machine_id.

OEE recap:
  Availability = run_time / planned_time         (downtime hurts this)
  Performance  = actual output / ideal output    (uses product ideal cycle time)
  Quality      = good_units / total_units
  OEE          = Availability x Performance x Quality
"""

from pyspark.sql import functions as F

from config.spark_session import get_spark
from config.settings import BRONZE_PATH, SILVER_PATH, GOLD_PATH, STORAGE_FORMAT


def _load(spark, layer, name):
    return spark.read.format(STORAGE_FORMAT).load(f"{layer}/{name}")


def _write(df, name):
    out = f"{GOLD_PATH}/{name}"
    df.write.format(STORAGE_FORMAT).mode("overwrite").save(out)
    print(f"  {name:<22} rows={df.count():>4}  -> {out}")


def run():
    spark = get_spark("gold_marts")

    # --- load the clean inputs ------------------------------------------------
    runs = _load(spark, SILVER_PATH, "mes_runs")
    products = _load(spark, BRONZE_PATH, "dim_products")       # for ideal cycle time
    machines = (_load(spark, SILVER_PATH, "dim_machine_scd2")   # current machine context
                .filter("is_current")
                .select("machine_id", "machine_name", "line", "machine_type"))
    sensors = _load(spark, SILVER_PATH, "sensors")
    quality = _load(spark, SILVER_PATH, "quality")

    # --- per-run OEE components ----------------------------------------------
    r = runs.join(products.select("product_id", "ideal_cycle_time_sec"), "product_id", "left")
    r = (r
         .withColumn("run_time_min", F.col("planned_production_min") - F.col("downtime_min"))
         .withColumn("availability", F.col("run_time_min") / F.col("planned_production_min"))
         # performance can drift slightly above 1 on noisy data -> cap at 1.0
         .withColumn("performance", F.least(
             (F.col("ideal_cycle_time_sec") * F.col("total_units"))
             / (F.col("run_time_min") * 60.0), F.lit(1.0)))
         .withColumn("quality", F.col("good_units") / F.col("total_units"))
         .withColumn("oee", F.col("availability") * F.col("performance") * F.col("quality"))
         .withColumn("scrap_units", F.col("total_units") - F.col("good_units")))

    # --- MART 1: OEE by machine ----------------------------------------------
    oee_machine = (r.groupBy("machine_id")
                   .agg(F.round(F.avg("availability"), 3).alias("avg_availability"),
                        F.round(F.avg("performance"), 3).alias("avg_performance"),
                        F.round(F.avg("quality"), 3).alias("avg_quality"),
                        F.round(F.avg("oee"), 3).alias("avg_oee"),
                        F.sum("downtime_min").alias("total_downtime_min"),
                        F.sum("total_units").alias("total_units"),
                        F.sum("scrap_units").alias("total_scrap"))
                   .withColumn("scrap_rate",
                               F.round(F.col("total_scrap") / F.col("total_units"), 3))
                   .join(machines, "machine_id", "left")
                   .orderBy("machine_id"))
    _write(oee_machine, "gold_oee_by_machine")

    # --- MART 2: OEE by line -------------------------------------------------
    oee_line = (r.join(machines.select("machine_id", "line"), "machine_id", "left")
                .groupBy("line")
                .agg(F.round(F.avg("oee"), 3).alias("avg_oee"),
                     F.sum("downtime_min").alias("total_downtime_min"),
                     F.sum("total_units").alias("total_units"))
                .orderBy("line"))
    _write(oee_line, "gold_oee_by_line")

    # --- MART 3: machine health (the three-source join) ----------------------
    sensor_agg = (sensors.groupBy("machine_id")
                  .agg(F.round(F.avg("temperature_c"), 1).alias("avg_temp_c"),
                       F.round(F.max("temperature_c"), 1).alias("max_temp_c"),
                       F.round(F.avg("tool_wear_min"), 1).alias("avg_tool_wear"),
                       F.sum(F.col("machine_failure").cast("int")).alias("sensor_failures")))

    quality_agg = (quality.groupBy("machine_id")
                   .agg(F.count("*").alias("inspections"),
                        F.sum(F.when(F.col("result") == "FAIL", 1).otherwise(0)).alias("fails"))
                   .withColumn("fail_rate", F.round(F.col("fails") / F.col("inspections"), 3)))

    health = (machines
              .join(oee_machine.select("machine_id", "avg_oee", "total_downtime_min"), "machine_id", "left")
              .join(sensor_agg, "machine_id", "left")
              .join(quality_agg.select("machine_id", "inspections", "fail_rate"), "machine_id", "left")
              .orderBy("machine_id"))
    _write(health, "gold_machine_health")

    print("Gold marts complete.")
    spark.stop()


if __name__ == "__main__":
    run()
