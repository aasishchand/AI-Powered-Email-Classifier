# Data Pipeline (Spark, Hive, Airflow)

- **sql/hive_warehouse_ddl.sql** – Hive star schema (fact_emails, dim_*). Create when using Hive.
- **spark/email_preprocessing.py** – PySpark job: read raw Parquet, clean text, tokenize, TF-IDF; write to processed layer.
- **airflow/dags/email_classification_dag.py** – DAG stub: ingest → preprocess → feature_eng → train → load_warehouse.

Run Spark job (when raw data exists on HDFS):

```bash
spark-submit spark/email_preprocessing.py
```

Run full stack with Docker (see root README); backend uses mock data when Hive/Spark are not connected.
