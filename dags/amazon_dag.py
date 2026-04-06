from datetime import datetime
from airflow.decorators import dag

from taskgroups.amazon_taskgroup import amazon_taskgroup


@dag(
    dag_id="amazon_scraper_dag",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
)
def amazon_dag():
    amazon_taskgroup()


amazon_dag()
