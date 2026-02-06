-- Hive star schema (fact + dimensions)
CREATE TABLE IF NOT EXISTS dim_date (date_key INT, full_date DATE, year INT) STORED AS PARQUET;
CREATE TABLE IF NOT EXISTS dim_sender (sender_key INT, sender_email STRING) STORED AS PARQUET;
CREATE TABLE IF NOT EXISTS dim_topic (topic_id INT, topic_name STRING) STORED AS PARQUET;
CREATE EXTERNAL TABLE IF NOT EXISTS fact_emails (message_id STRING, spam_label STRING, topic_id INT, body STRING, subject STRING) PARTITIONED BY (year INT, month INT) STORED AS PARQUET LOCATION '/warehouse/fact_emails/';
