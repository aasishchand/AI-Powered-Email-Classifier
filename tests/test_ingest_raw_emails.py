import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType


@pytest.fixture(scope="module")
def spark():
    return SparkSession.builder.master("local[1]").appName("test_ingest").getOrCreate()


def test_schema_fields(spark):
    schema = StructType([
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
    df = spark.createDataFrame([("id1", "Subj", "a@b.com", "p", "b", "2026-01-15 10:00:00", "", 0, 0)], schema)
    assert df.count() == 1
    assert len(df.schema.fields) == 9


def test_partition_columns(spark):
    from pyspark.sql import functions as F
    schema = StructType([
        StructField("message_id", StringType(), True),
        StructField("subject", StringType(), True),
    ])
    df = spark.createDataFrame([("id2", "Subj")], schema)
    df = df.withColumn("ingestion_date", F.lit("2026-01-16")).withColumn("mailbox_type", F.lit("faculty"))
    row = df.first()
    assert row.ingestion_date == "2026-01-16"
    assert row.mailbox_type == "faculty"


def test_empty_df(spark):
    schema = StructType([StructField("message_id", StringType(), True)])
    df = spark.createDataFrame([], schema)
    assert df.count() == 0
