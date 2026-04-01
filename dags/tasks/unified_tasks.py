from airflow.decorators import task
from airflow.utils.trigger_rule import TriggerRule

from core.constants.constants_values import AmazonConstants, FlipkartConstants


@task.branch(task_id="choose_source")
def choose_source(source: str) -> str:
    selected = (source or AmazonConstants.SOURCE).upper()
    if selected == FlipkartConstants.SOURCE:
        return "flipkart_scraper.insert_metadata"
    return "amazon_scraper.insert_metadata"


@task(
    task_id="merge_scraping",
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
)
def merge_scraping() -> str:
    return "selected_scraper_completed"
