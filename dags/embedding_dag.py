from datetime import datetime
from airflow.decorators import dag

from taskgroups.embedding_taskgroup import embedding_taskgroup


@dag(
    dag_id="embedding_pipeline_dag",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
)
def embedding_dag():
    embedding_taskgroup("embedding_pipeline")


embedding_dag()
