from airflow import DAG
from datetime import datetime

from taskgroups.amazon_taskgroup import amazon_taskgroup


with DAG(
    dag_id="amazon_scraper_dag",
    start_date=datetime(2024,1,1),
    schedule=None,
    catchup=False
):

    amazon_taskgroup()