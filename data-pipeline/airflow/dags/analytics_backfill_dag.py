"""Analytics backfill: manual trigger."""
from datetime import datetime
from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

with DAG(
    dag_id="analytics_backfill",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["analytics", "backfill"],
) as dag:
    spark_backfill = SparkSubmitOperator(
        task_id="spark_analytics_backfill",
        application="/opt/airflow/spark/jobs/compute_analytics.py",
        application_args=["--days", "30"],
        conn_id="spark_default",
        verbose=True,
    )
