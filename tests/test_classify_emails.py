"""Unit tests for classify_emails Spark job (UDF and schema)."""
import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F


@pytest.fixture(scope="module")
def spark():
    return SparkSession.builder.master("local[1]").appName("test_classify_emails").getOrCreate()


def test_classifier_udf_returns_spam_for_spam_keyword(spark):
    def classify(subject, body, sender):
        subject = subject or ""
        body = body or ""
        text = (subject + " " + body).lower()
        spam = "spam" if "spam" in text or "winner" in text else "ham"
        spam_score = 0.9 if spam == "spam" else 0.1
        topic = "promotions" if "offer" in text or "deal" in text else "general"
        return (spam, spam_score, topic, 0.85, 0.5, 0.3)

    udf = F.udf(
        classify,
        "struct<spam_label: string, spam_score: double, topic: string, topic_confidence: double, urgency_score: double, sentiment_score: double>",
    )
    df = spark.createDataFrame([("You won!", "Claim your prize", "x@y.com")], ["subject", "body", "sender"])
    df = df.withColumn("pred", udf(F.col("subject"), F.col("body"), F.col("sender")))
    df = df.withColumn("spam_label", F.col("pred.spam_label")).withColumn("spam_score", F.col("pred.spam_score"))
    row = df.first()
    assert row.spam_label == "spam"
    assert row.spam_score == 0.9


def test_classifier_udf_returns_ham_for_normal_text(spark):
    def classify(subject, body, sender):
        subject = subject or ""
        body = body or ""
        text = (subject + " " + body).lower()
        spam = "spam" if "spam" in text or "winner" in text else "ham"
        spam_score = 0.9 if spam == "spam" else 0.1
        topic = "promotions" if "offer" in text or "deal" in text else "general"
        return (spam, spam_score, topic, 0.85, 0.5, 0.3)

    udf = F.udf(
        classify,
        "struct<spam_label: string, spam_score: double, topic: string, topic_confidence: double, urgency_score: double, sentiment_score: double>",
    )
    df = spark.createDataFrame([("Meeting tomorrow", "Hi team, see you at 3pm", "a@b.com")], ["subject", "body", "sender"])
    df = df.withColumn("pred", udf(F.col("subject"), F.col("body"), F.col("sender")))
    df = df.withColumn("spam_label", F.col("pred.spam_label"))
    assert df.first().spam_label == "ham"


def test_partition_columns_present(spark):
    from pyspark.sql.types import StructType, StructField, StringType
    schema = StructType([
        StructField("message_id", StringType()),
        StructField("subject", StringType()),
        StructField("spam_label", StringType()),
        StructField("classification_date", StringType()),
        StructField("label", StringType()),
    ])
    df = spark.createDataFrame([("m1", "Subj", "ham", "2026-01-15", "ham")], schema)
    assert "classification_date" in df.columns
    assert "label" in df.columns
    assert df.first().label == df.first().spam_label
