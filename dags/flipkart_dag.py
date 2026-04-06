from datetime import datetime
from airflow.decorators import dag

from taskgroups.flipkart_taskgroup import flipkart_taskgroup


@dag(
    dag_id="flipkart_scraper_dag",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
)
def flipkart_dag():
    flipkart_taskgroup()


flipkart_dag()
