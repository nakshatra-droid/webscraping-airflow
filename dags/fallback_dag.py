from datetime import datetime

from airflow.decorators import dag
from airflow.models.param import Param

from core.constants.constants_values import AmazonConstants, FlipkartConstants
from taskgroups.fallback_taskgroup import fallback_taskgroup


@dag(
    dag_id="fallback_scraper_dag",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    params={
        "source": Param(
            AmazonConstants.SOURCE,
            type="string",
            enum=[AmazonConstants.SOURCE, FlipkartConstants.SOURCE],
            description="Choose which fallback scraper source to run",
        )
    },
)
def fallback_dag():
    fallback_taskgroup(source="{{ params.source }}")


fallback_dag()
