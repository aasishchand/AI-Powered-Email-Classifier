#!/usr/bin/env python3
"""Ingest raw email JSON from MinIO into Hive emails_raw as Parquet."""
import argparse
import logging
import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

SCHEMA = StructType([
    StructField("message_id", StringType(), True),
    StructField("subject", StringType(), True),
    StructField("sender", StringType(), True),
    StructField("body_preview", StringType(), True),
    StructField("body", StringType(), True),
    StructField("received_at", StringType(), True),
    StructField("raw_headers", StringType(), True),
    StructField("attachment_count", IntegerType(), True),
    StructField("cc_count", IntegerType(), True),
])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="Ingestion date YYYY-MM-DD")
    parser.add_argument("--mailbox-type", default="faculty")
    parser.add_argument("--minio-endpoint", default=None)
    parser.add_argument("--metastore-uri", default=None)
    args = parser.parse_args()

    bucket_raw = os.environ.get("MINIO_BUCKET_RAW", "emails-raw")
    spark = SparkSession.builder.appName("ingest_raw_emails").enableHiveSupport().getOrCreate()

    base_path = "s3a://%s/raw/emails/%s/" % (bucket_raw, args.date)
    json_path = base_path + "*/*.json"
    try:
        df = spark.read.schema(SCHEMA).json(json_path)
    except Exception as e:
        logger.warning("No JSON at %s: %s", json_path, e)
        df = spark.createDataFrame([], SCHEMA)

    df = (
        df.withColumn("subject", F.coalesce(F.col("subject"), F.lit("")))
        .withColumn("sender", F.coalesce(F.col("sender"), F.lit("")))
        .withColumn("body_preview", F.coalesce(F.col("body_preview"), F.lit("")))
        .withColumn("body", F.coalesce(F.col("body"), F.lit("")))
        .withColumn("raw_headers", F.coalesce(F.col("raw_headers"), F.lit("")))
        .withColumn("attachment_count", F.coalesce(F.col("attachment_count"), F.lit(0)))
        .withColumn("cc_count", F.coalesce(F.col("cc_count"), F.lit(0)))
        .withColumn("received_at_ts", F.to_timestamp(F.col("received_at")))
        .drop("received_at")
        .withColumnRenamed("received_at_ts", "received_at")
        .withColumn("ingestion_date", F.lit(args.date))
        .withColumn("mailbox_type", F.lit(args.mailbox_type))
    )
    count = df.count()
    logger.info("Record count: %d", count)

    output_path = "s3a://%s/emails_raw/ingestion_date=%s/mailbox_type=%s" % (
        bucket_raw, args.date, args.mailbox_type)
    df.write.mode("overwrite").parquet(output_path)
    logger.info("Wrote Parquet to %s", output_path)

    try:
        spark.sql(
            "ALTER TABLE emails_raw ADD IF NOT EXISTS PARTITION "
            "(ingestion_date='%s', mailbox_type='%s') LOCATION '%s'"
            % (args.date, args.mailbox_type, output_path)
        )
    except Exception as e:
        logger.debug("Hive add partition: %s", e)
    spark.stop()


if __name__ == "__main__":
    main()
