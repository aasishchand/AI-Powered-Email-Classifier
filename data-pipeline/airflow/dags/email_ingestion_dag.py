from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

def noop(**ctx):
    pass

def notify_api(**ctx):
    import requests
    url = "http://backend:8000/api/v1/bigdata/analytics/refresh"
    requests.post(url, timeout=30)

with DAG(
    dag_id="email_ingestion_pipeline",
    schedule="@hourly",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["email", "ingestion"],
) as dag:
    t1 = PythonOperator(task_id="fetch_emails_task", python_callable=noop)
    t2 = PythonOperator(task_id="push_to_kafka_task", python_callable=noop)
    t3 = PythonOperator(task_id="consume_kafka_to_minio_task", python_callable=noop)
    t4 = SparkSubmitOperator(
        task_id="spark_ingest_raw",
        application="/opt/airflow/spark/jobs/ingest_raw_emails.py",
        application_args=["--date", "{{ ds }}", "--mailbox-type", "faculty"],
        conn_id="spark_default",
        verbose=True,
    )
    t5 = SparkSubmitOperator(
        task_id="spark_classify",
        application="/opt/airflow/spark/jobs/classify_emails.py",
        application_args=["--date", "{{ ds }}"],
        conn_id="spark_default",
        verbose=True,
    )
    t6 = SparkSubmitOperator(
        task_id="spark_analytics",
        application="/opt/airflow/spark/jobs/compute_analytics.py",
        application_args=["--end-date", "{{ ds }}", "--days", "30"],
        conn_id="spark_default",
        verbose=True,
    )
    t7 = PythonOperator(task_id="notify_api_task", python_callable=notify_api)
    t1 >> t2 >> t3 >> t4 >> t5 >> t6 >> t7
