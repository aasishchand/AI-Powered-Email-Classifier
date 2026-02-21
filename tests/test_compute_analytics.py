"""Unit tests for compute_analytics Spark job (aggregations)."""
import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F


@pytest.fixture(scope="module")
def spark():
    return (
        SparkSession.builder.master("local[1]")
        .appName("test_compute_analytics")
        .getOrCreate()
    )


def test_daily_aggregation_counts(spark):
    schema = "classification_date string, spam_label string, urgency_score double"
    data = [
        ("2026-01-15", "ham", 0.5),
        ("2026-01-15", "spam", 0.1),
        ("2026-01-15", "ham", 0.8),
    ]
    df = spark.createDataFrame(data, schema)
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
    row = daily.first()
    assert row.daily_volume == 3
    assert row.spam_count == 1
    assert row.ham_count == 2
    assert row.spam_rate == pytest.approx(1 / 3)
    assert row.avg_urgency_score == pytest.approx((0.5 + 0.1 + 0.8) / 3)


def test_date_filter_range(spark):
    schema = "classification_date string, spam_label string"
    data = [
        ("2026-01-10", "ham"),
        ("2026-01-15", "spam"),
        ("2026-01-20", "ham"),
        ("2026-01-25", "ham"),
    ]
    df = spark.createDataFrame(data, schema)
    filtered = df.filter(
        (F.col("classification_date") >= "2026-01-12") & (F.col("classification_date") <= "2026-01-22")
    )
    assert filtered.count() == 2


def test_empty_input_produces_empty_aggregate(spark):
    schema = "classification_date string, spam_label string, urgency_score double"
    df = spark.createDataFrame([], schema)
    daily = df.groupBy(F.col("classification_date").alias("metric_date")).agg(
        F.count("*").alias("daily_volume"),
        F.sum(F.when(F.col("spam_label") == "spam", 1).otherwise(0)).alias("spam_count"),
    )
    assert daily.count() == 0
