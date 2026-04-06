from airflow.decorators import task
from core.scraping.amazon_scraping import AmazonScraping


@task
def insert_metadata():
    return AmazonScraping.insert_metadata()


@task
def fetch_existing_urls():
    return list(AmazonScraping.fetch_existing_urls())


@task
def collect_urls(existing_urls):
    return AmazonScraping.collect_urls(existing_urls)


@task
def scrape_products(urls):
    return AmazonScraping.scrape_products(urls)


@task
def validate_products(products):
    return AmazonScraping.validate_products(products)


@task
def update_data(metadata_run_id, stats):
    AmazonScraping.update_data(metadata_run_id, stats)
