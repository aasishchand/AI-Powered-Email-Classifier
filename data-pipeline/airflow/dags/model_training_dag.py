from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.short_circuit import ShortCircuitOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

def check_data(**ctx):
    return True

def eval_model(**ctx):
    pass

def promote(**ctx):
    pass

with DAG(
    dag_id="model_training_pipeline",
    schedule="0 2 * * 0",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["model", "training"],
) as dag:
    check = ShortCircuitOperator(task_id="check_new_data_task", python_callable=check_data)
    train = SparkSubmitOperator(
        task_id="spark_train_model",
        application="/opt/airflow/spark/jobs/train_model.py",
        application_args=[],
        conn_id="spark_default",
        verbose=True,
    )
    ev = PythonOperator(task_id="evaluate_model_task", python_callable=eval_model)
    prom = PythonOperator(task_id="promote_model_task", python_callable=promote)
    check >> train >> ev >> prom
