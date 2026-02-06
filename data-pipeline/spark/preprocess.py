# PySpark email preprocessing. Run: spark-submit preprocess.py
from pyspark.sql import SparkSession
from pyspark.ml.feature import Tokenizer, StopWordsRemover, HashingTF, IDF
from pyspark.ml import Pipeline

spark = SparkSession.builder.appName("EmailPreprocess").getOrCreate()
df = spark.read.parquet("/email_platform/raw/emails/")
pipeline = Pipeline(stages=[
    Tokenizer(inputCol="body", outputCol="tokens"),
    StopWordsRemover(inputCol="tokens", outputCol="filtered"),
    HashingTF(inputCol="filtered", outputCol="raw_features", numFeatures=5000),
    IDF(inputCol="raw_features", outputCol="features")
])
model = pipeline.fit(df)
model.transform(df).write.mode("overwrite").parquet("/email_platform/processed/emails_tokenized/")
spark.stop()
