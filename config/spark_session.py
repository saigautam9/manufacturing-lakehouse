"""
Starts up Spark — the "engine" that does all the heavy lifting.

WHAT IS SPARK, in one breath: a program that can process huge amounts of data by
splitting the work across many CPU cores (and, on a real cluster, many machines)
at once. You write ordinary-looking code; Spark figures out how to run it in
parallel. A "SparkSession" is just your handle to that engine — you create one,
then use it to read and write data.

Why a separate file for this? Every job (bronze, silver, gold) needs the same
engine started the same way. Writing it once here keeps the pipeline code clean.
"""

from pyspark.sql import SparkSession
from config.settings import STORAGE_FORMAT


def get_spark(app_name: str) -> SparkSession:
    """Create (or reuse) a SparkSession, wired for Delta only if we asked for it."""
    builder = SparkSession.builder.appName(app_name)

    # When STORAGE_FORMAT is "delta" (i.e. on Databricks), we switch on Delta's
    # extra powers. Locally we skip this block entirely and Spark stays vanilla.
    if STORAGE_FORMAT == "delta":
        builder = (
            builder
            .config("spark.sql.extensions",
                    "io.delta.sql.DeltaSparkSessionExtension")
            .config("spark.sql.catalog.spark_catalog",
                    "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        )
        spark = builder.getOrCreate()
    else:
        # Local / parquet mode: nothing special needed.
        spark = builder.getOrCreate()

    # Quiet Spark down to ERROR so the console shows our output, not benign warnings
    # (e.g. the harmless FileStreamSink probe on wildcard batch paths).
    spark.sparkContext.setLogLevel("ERROR")
    return spark
