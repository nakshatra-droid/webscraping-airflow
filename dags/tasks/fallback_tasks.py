from airflow.decorators import task

from core.scraping.fallback_scraping import FallbackScraping


@task
def insert_metadata():
    return FallbackScraping.insert_metadata()


@task
def collect_urls(source):
    return FallbackScraping.collect_urls(source)


@task
def scrape_products(source, activity_batch):
    return FallbackScraping.scrape_products(source, activity_batch)


@task
def validate_products(source, products):
    return FallbackScraping.validate_products(source, products)


@task
def update_data(metadata_run_id, source, stats):
    FallbackScraping.update_data(metadata_run_id, source, stats)
