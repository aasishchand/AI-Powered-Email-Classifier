-- Hive/SparkSQL DDL for AI-Powered-Email-Classifier big data warehouse
-- Tables use S3A (MinIO) locations. Run from Spark with Hive support or via spark-sql.

-- Raw emails (from Kafka consumer / batch upload)
-- Partitioned by ingestion_date and mailbox_type for efficient pruning
CREATE EXTERNAL TABLE IF NOT EXISTS emails_raw (
    message_id STRING,
    subject STRING,
    sender STRING,
    body_preview STRING,
    body STRING,
    received_at TIMESTAMP,
    raw_headers STRING,
    attachment_count INT,
    cc_count INT
)
PARTITIONED BY (ingestion_date STRING, mailbox_type STRING)
STORED AS PARQUET
LOCATION 's3a://emails-raw/emails_raw/'
TBLPROPERTIES ('parquet.compression' = 'SNAPPY');

-- Classified emails (output of classify_emails Spark job)
CREATE EXTERNAL TABLE IF NOT EXISTS emails_classified (
    message_id STRING,
    subject STRING,
    sender STRING,
    body_preview STRING,
    received_at TIMESTAMP,
    spam_label STRING,
    spam_score DOUBLE,
    topic STRING,
    topic_confidence DOUBLE,
    urgency_score DOUBLE,
    sentiment_score DOUBLE,
    ingestion_date STRING,
    mailbox_type STRING
)
PARTITIONED BY (classification_date STRING, label STRING)
STORED AS PARQUET
LOCATION 's3a://emails-processed/emails_classified/'
TBLPROPERTIES ('parquet.compression' = 'SNAPPY');

-- Flat feature table for ML training (tokenized + hashed features)
CREATE EXTERNAL TABLE IF NOT EXISTS email_features (
    message_id STRING,
    label STRING,
    topic STRING,
    subject_tf_idf ARRAY<DOUBLE>,
    body_tf_idf ARRAY<DOUBLE>,
    sender_domain STRING,
    received_at TIMESTAMP,
    training_date STRING
)
STORED AS ORC
LOCATION 's3a://emails-processed/email_features/'
TBLPROPERTIES ('orc.compress' = 'SNAPPY');

-- Pre-aggregated daily analytics (materialized by compute_analytics job)
CREATE EXTERNAL TABLE IF NOT EXISTS analytics_daily (
    metric_date STRING,
    daily_volume BIGINT,
    spam_count BIGINT,
    spam_rate DOUBLE,
    ham_count BIGINT,
    topic_distribution MAP<STRING,BIGINT>,
    avg_urgency_score DOUBLE,
    top_senders_by_domain ARRAY<STRUCT<domain:STRING, count:BIGINT>>,
    updated_at TIMESTAMP
)
STORED AS PARQUET
LOCATION 's3a://emails-processed/analytics_daily/'
TBLPROPERTIES ('parquet.compression' = 'SNAPPY');

-- Model registry: version, metrics, S3 path, champion flag
CREATE EXTERNAL TABLE IF NOT EXISTS model_registry (
    version STRING,
    training_date STRING,
    accuracy DOUBLE,
    f1 DOUBLE,
    model_path STRING,
    is_champion BOOLEAN,
    created_at TIMESTAMP
)
STORED AS PARQUET
LOCATION 's3a://email-models/model_registry/'
TBLPROPERTIES ('parquet.compression' = 'SNAPPY');
