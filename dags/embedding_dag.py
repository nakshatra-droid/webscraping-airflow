from airflow import DAG
from datetime import datetime

from taskgroups.embedding_taskgroup import embedding_taskgroup


with DAG(
    dag_id="embedding_pipeline_dag",
    start_date=datetime(2024,1,1),
    schedule=None,
    catchup=False
):

    embedding_taskgroup("embedding_pipeline")