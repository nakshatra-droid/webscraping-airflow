from airflow import DAG
from datetime import datetime
from airflow.decorators import task
from airflow.models.param import Param
from airflow.utils.trigger_rule import TriggerRule

from taskgroups.amazon_taskgroup import amazon_taskgroup
from taskgroups.flipkart_taskgroup import flipkart_taskgroup
from taskgroups.embedding_taskgroup import embedding_taskgroup


with DAG(
    dag_id="unified_pipeline_dag",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    params={
        "source": Param(
            "AMAZON",
            type="string",
            enum=["AMAZON", "FLIPKART"],
            description="Choose which scraping flow to run",
        )
    },
):

    @task.branch(task_id="choose_source")
    def choose_source(source: str) -> str:
        selected = (source or "AMAZON").upper()
        if selected == "FLIPKART":
            return "flipkart_scraper.insert_metadata"
        return "amazon_scraper.insert_metadata"

    selected_source = choose_source(source="{{ params.source }}")

    amazon = amazon_taskgroup()

    flipkart = flipkart_taskgroup()

    @task(
        task_id="merge_scraping",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )
    def merge_scraping_task() -> str:
        return "selected_scraper_completed"

    merge_scraping = merge_scraping_task()

    embedding = embedding_taskgroup("embedding")

    selected_source >> [amazon, flipkart]
    amazon >> merge_scraping
    flipkart >> merge_scraping
    merge_scraping >> embedding
