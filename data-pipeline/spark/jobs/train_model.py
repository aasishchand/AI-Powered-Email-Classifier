#!/usr/bin/env python3
"""
PySpark ML job: read email_features, train Pipeline (Tokenizer -> HashingTF -> IDF -> LogisticRegression),
evaluate with CrossValidator, save model to MinIO and register in model_registry.
"""
import argparse
import logging
import os
import sys
from datetime import datetime
from pyspark.ml import Pipeline
from pyspark.ml.classification import LogisticRegression
from pyspark.ml.evaluation import BinaryClassificationEvaluator, MulticlassClassificationEvaluator
from pyspark.ml.feature import HashingTF, IDF, Tokenizer
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=None, help="Model version tag (default: timestamp)")
    parser.add_argument("--minio-endpoint", default=None)
    parser.add_argument("--metastore-uri", default=None)
    args = parser.parse_args()

    version = args.version or datetime.utcnow().strftime("%Y%m%d%H%M")
    bucket_processed = os.environ.get("MINIO_BUCKET_PROCESSED", "emails-processed")
    bucket_models = os.environ.get("MINIO_BUCKET_MODELS", "email-models")

    spark = (
        SparkSession.builder.appName("train_model")
        .enableHiveSupport()
        .getOrCreate()
    )

    # Read email_features (ORC) or fallback to emails_classified to build features on the fly
    features_path = f"s3a://{bucket_processed}/email_features/"
    try:
        df = spark.read.orc(features_path)
    except Exception:
        # Build minimal features from emails_classified if no email_features yet
        classified_path = f"s3a://{bucket_processed}/emails_classified/"
        try:
            df = spark.read.parquet(classified_path).limit(5000)
        except Exception as e:
            logger.warning("No email_features or emails_classified: %s. Exiting.", e)
            spark.stop()
            return
        df = (
            df.withColumn("text", F.coalesce(F.col("subject"), F.lit("")) + F.lit(" ") + F.coalesce(F.col("body_preview"), F.lit("")))
            .withColumn("label", F.when(F.col("spam_label") == "spam", 1).otherwise(0))
            .withColumn("training_date", F.lit(datetime.utcnow().strftime("%Y-%m-%d")))
        )

    if "text" not in df.columns:
        df = df.withColumn("text", F.coalesce(F.col("body_preview"), F.lit("")))
    if "label" not in df.columns:
        df = df.withColumn("label", F.when(F.col("spam_label") == "spam", 1).otherwise(0))

    tokenizer = Tokenizer(inputCol="text", outputCol="words")
    hashing_tf = HashingTF(inputCol="words", outputCol="raw_features", numFeatures=1000)
    idf = IDF(inputCol="raw_features", outputCol="features")
    lr = LogisticRegression(maxIter=20, regParam=0.01, featuresCol="features", labelCol="label")
    pipeline = Pipeline(stages=[tokenizer, hashing_tf, idf, lr])

    evaluator = BinaryClassificationEvaluator(labelCol="label", rawPredictionCol="rawPrediction", metricName="areaUnderROC")
    evaluator_f1 = MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction", metricName="f1")

    grid = ParamGridBuilder().addGrid(lr.regParam, [0.01, 0.1]).build()
    cv = CrossValidator(estimator=pipeline, estimatorParamMaps=grid, evaluator=evaluator, numFolds=5)
    model = cv.fit(df)
    predictions = model.transform(df)
    accuracy = predictions.filter(F.col("prediction") == F.col("label")).count() / max(predictions.count(), 1)
    f1 = evaluator_f1.evaluate(predictions)
    auc = evaluator.evaluate(predictions)

    logger.info("Accuracy: %.4f, F1: %.4f, AUC: %.4f", accuracy, f1, auc)

    # Save model to MinIO (Spark ML Persist)
    model_path = f"s3a://{bucket_models}/models/v{version}/"
    model.bestModel.save(model_path)
    logger.info("Saved model to %s", model_path)

    # Register in model_registry (write Parquet row)
    registry_path = f"s3a://{bucket_models}/model_registry/"
    from pyspark.sql.types import StructType, StructField, StringType, DoubleType, BooleanType, TimestampType
    reg_schema = StructType([
        StructField("version", StringType()),
        StructField("training_date", StringType()),
        StructField("accuracy", DoubleType()),
        StructField("f1", DoubleType()),
        StructField("model_path", StringType()),
        StructField("is_champion", BooleanType()),
        StructField("created_at", TimestampType()),
    ])
    reg_row = spark.createDataFrame([(
        version,
        datetime.utcnow().strftime("%Y-%m-%d"),
        float(accuracy),
        float(f1),
        model_path,
        True,  # New model marked champion for now
        datetime.utcnow(),
    )], reg_schema)
    # Append to existing registry if any
    try:
        existing = spark.read.parquet(registry_path)
        existing = existing.withColumn("is_champion", F.lit(False))
        reg_row = reg_row.unionByName(existing, allowMissingColumns=True)
    except Exception:
        pass
    reg_row.write.mode("overwrite").parquet(registry_path)
    logger.info("Registered model in model_registry at %s", registry_path)

    spark.stop()


if __name__ == "__main__":
    main()
