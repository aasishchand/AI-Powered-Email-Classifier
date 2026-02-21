#!/usr/bin/env python3
"""Classify emails from emails_raw and write to emails_classified; write summary JSON to MinIO."""
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


def make_classifier_udf(spark):
    def classify(subject, body, sender):
        subject = subject or ""
        body = body or ""
        text = (subject + " " + body).lower()
        spam = "spam" if "spam" in text or "winner" in text else "ham"
        spam_score = 0.9 if spam == "spam" else 0.1
        topic = "promotions" if "offer" in text or "deal" in text else "general"
        return (spam, spam_score, topic, 0.85, 0.5, 0.3)
    return F.udf(
        classify,
        "struct<spam_label: string, spam_score: double, topic: string, topic_confidence: double, urgency_score: double, sentiment_score: double>",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--mailbox-type", default=None)
    args = parser.parse_args()

    bucket_raw = os.environ.get("MINIO_BUCKET_RAW", "emails-raw")
    bucket_processed = os.environ.get("MINIO_BUCKET_PROCESSED", "emails-processed")

    spark = SparkSession.builder.appName("classify_emails").enableHiveSupport().getOrCreate()

    base = f"s3a://{bucket_raw}/emails_raw/ingestion_date={args.date}/"
    path = f"{base}mailbox_type={args.mailbox_type}/" if args.mailbox_type else base
    try:
        df = spark.read.parquet(path)
    except Exception as e:
        logger.warning("No data at %s: %s", path, e)
        spark.stop()
        return

    classify_udf = make_classifier_udf(spark)
    df = df.withColumn(
        "pred",
        classify_udf(F.col("subject"), F.coalesce(F.col("body"), F.col("body_preview")), F.col("sender")),
    )
    df = (
        df.withColumn("spam_label", F.col("pred.spam_label"))
        .withColumn("spam_score", F.col("pred.spam_score"))
        .withColumn("topic", F.col("pred.topic"))
        .withColumn("topic_confidence", F.col("pred.topic_confidence"))
        .withColumn("urgency_score", F.col("pred.urgency_score"))
        .withColumn("sentiment_score", F.col("pred.sentiment_score"))
        .withColumn("classification_date", F.lit(args.date))
        .withColumn("label", F.col("pred.spam_label"))
        .drop("pred")
    )

    out_base = f"s3a://{bucket_processed}/emails_classified/"
    df.write.mode("overwrite").partitionBy("classification_date", "label").parquet(out_base)

    summary = {
        "date": args.date,
        "total": int(df.count()),
        "spam_count": int(df.filter(F.col("spam_label") == "spam").count()),
        "ham_count": int(df.filter(F.col("spam_label") == "ham").count()),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    uri = f"s3a://{bucket_processed}/processed/summaries/{args.date}.json"
    try:
        sc = spark.sparkContext
        conf = sc._jsc.sc().hadoopConfiguration()
        conf.set("fs.s3a.endpoint", os.environ.get("MINIO_ENDPOINT", "http://localhost:9000"))
        conf.set("fs.s3a.access.key", os.environ.get("MINIO_ROOT_USER", "minioadmin"))
        conf.set("fs.s3a.secret.key", os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin"))
        conf.set("fs.s3a.path.style.access", "true")
        fs = sc._jvm.org.apache.hadoop.fs.FileSystem.get(conf)
        path_obj = sc._jvm.org.apache.hadoop.fs.Path(uri)
        out = fs.create(path_obj, True)
        out.write(json.dumps(summary).encode("utf-8"))
        out.close()
        logger.info("Wrote summary to %s", uri)
    except Exception as e:
        logger.warning("Could not write summary: %s", e)
    spark.stop()


if __name__ == "__main__":
    main()
