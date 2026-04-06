from datetime import datetime
from airflow.decorators import dag
from airflow.models.param import Param

from taskgroups.amazon_taskgroup import amazon_taskgroup
from taskgroups.flipkart_taskgroup import flipkart_taskgroup
from taskgroups.embedding_taskgroup import embedding_taskgroup
from tasks.unified_tasks import choose_source, merge_scraping
from core.constants.constants_values import AmazonConstants, FlipkartConstants


@dag(
    dag_id="unified_pipeline_dag",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    params={
        "source": Param(
            AmazonConstants.SOURCE,
            type="string",
            enum=[AmazonConstants.SOURCE, FlipkartConstants.SOURCE],
            description="Choose which scraping flow to run",
        )
    },
)
def unified_dag():
    selected_source = choose_source(source="{{ params.source }}")

    amazon = amazon_taskgroup()

    flipkart = flipkart_taskgroup()

    merge_scraping_task = merge_scraping()

    embedding = embedding_taskgroup("embedding")

    selected_source >> [amazon, flipkart]
    amazon >> merge_scraping_task
    flipkart >> merge_scraping_task
    merge_scraping_task >> embedding


unified_dag()
