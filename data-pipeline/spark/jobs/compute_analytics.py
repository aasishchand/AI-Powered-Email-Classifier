#!/usr/bin/env python3
"""
PySpark job: read emails_classified for a 30-day window, compute daily metrics,
write to analytics_daily and to MinIO as JSON.
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, LongType, DoubleType, MapType, TimestampType

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--minio-endpoint", default=None)
    parser.add_argument("--metastore-uri", default=None)
    args = parser.parse_args()

    end = args.end_date or datetime.utcnow().strftime("%Y-%m-%d")
    start_dt = datetime.strptime(end, "%Y-%m-%d") - timedelta(days=args.days)
    start = start_dt.strftime("%Y-%m-%d")
    bucket_processed = os.environ.get("MINIO_BUCKET_PROCESSED", "emails-processed")

    spark = SparkSession.builder.appName("compute_analytics").enableHiveSupport().getOrCreate()

    base = f"s3a://{bucket_processed}/emails_classified/"
    try:
        df = spark.read.parquet(base).filter(
            (F.col("classification_date") >= start) & (F.col("classification_date") <= end)
        )
    except Exception as e:
        logger.warning("No data: %s.", e)
        schema = StructType([
            StructField("metric_date", StringType()),
            StructField("daily_volume", LongType()),
            StructField("spam_count", LongType()),
            StructField("spam_rate", DoubleType()),
            StructField("ham_count", LongType()),
            StructField("topic_distribution", MapType(StringType(), LongType())),
            StructField("avg_urgency_score", DoubleType()),
            StructField("updated_at", TimestampType()),
        ])
        empty = spark.createDataFrame([], schema)
        empty.write.mode("overwrite").parquet(f"s3a://{bucket_processed}/analytics_daily/")
        spark.stop()
        return

    daily = df.groupBy(F.col("classification_date").alias("metric_date")).agg(
        F.count("*").alias("daily_volume"),
        F.sum(F.when(F.col("spam_label") == "spam", 1).otherwise(0)).alias("spam_count"),
        F.sum(F.when(F.col("spam_label") == "ham", 1).otherwise(0)).alias("ham_count"),
        F.avg("urgency_score").alias("avg_urgency_score"),
    )
    daily = daily.withColumn(
        "spam_rate",
        F.when(F.col("daily_volume") > 0, F.col("spam_count") / F.col("daily_volume")).otherwise(F.lit(0.0)),
    )

    topic_df = (
        df.groupBy("classification_date", "topic")
        .count()
        .groupBy("classification_date")
        .agg(F.map_from_entries(F.collect_list(F.struct(F.col("topic"), F.col("count")))).alias("topic_map"))
    )
    daily = daily.join(topic_df, daily.metric_date == topic_df.classification_date, "left").drop(
        topic_df.classification_date
    ).withColumnRenamed("topic_map", "topic_distribution")
    daily = daily.withColumn("updated_at", F.current_timestamp())

    out_path = f"s3a://{bucket_processed}/analytics_daily/"
    daily.write.mode("overwrite").parquet(out_path)
    logger.info("Wrote analytics_daily to %s", out_path)

    for row in daily.collect():
        metric_date = row.metric_date
        topic_dist = row.topic_distribution.asDict() if row.topic_distribution else {}
        payload = {
            "metric_date": metric_date,
            "daily_volume": row.daily_volume,
            "spam_count": row.spam_count,
            "spam_rate": float(row.spam_rate),
            "ham_count": row.ham_count,
            "topic_distribution": dict(topic_dist),
            "avg_urgency_score": float(row.avg_urgency_score or 0),
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        uri = f"s3a://{bucket_processed}/analytics/daily/{metric_date}.json"
        try:
            sc = spark.sparkContext
            conf = sc._jsc.sc().hadoopConfiguration()
            conf.set("fs.s3a.endpoint", os.environ.get("MINIO_ENDPOINT", "http://localhost:9000"))
            conf.set("fs.s3a.access.key", os.environ.get("MINIO_ROOT_USER", "minioadmin"))
            conf.set("fs.s3a.secret.key", os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin"))
            conf.set("fs.s3a.path.style.access", "true")
            fs = sc._jvm.org.apache.hadoop.fs.FileSystem.get(conf)
            path = sc._jvm.org.apache.hadoop.fs.Path(uri)
            out = fs.create(path, True)
            out.write(json.dumps(payload, default=str).encode("utf-8"))
            out.close()
            logger.info("Wrote %s", uri)
        except Exception as e:
            logger.warning("Write JSON failed: %s", e)

    spark.stop()


if __name__ == "__main__":
    main()
