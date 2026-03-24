from airflow import DAG
from datetime import datetime

from taskgroups.flipkart_taskgroup import flipkart_taskgroup


with DAG(
    dag_id="flipkart_scraper_dag",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
):
    flipkart_taskgroup()
