from airflow.decorators import task
from core.scraping.flipkart_scraping import FlipkartScraping


@task
def insert_metadata():
    return FlipkartScraping.insert_metadata()


@task
def fetch_existing_urls():
    return list(FlipkartScraping.fetch_existing_urls())


@task
def collect_urls(existing_urls):
    return FlipkartScraping.collect_urls(existing_urls)


@task
def scrape_products(urls):
    return FlipkartScraping.scrape_products(urls)


@task
def validate_products(products):
    return FlipkartScraping.validate_products(products)


@task
def update_data(metadata_run_id, stats):
    FlipkartScraping.update_data(metadata_run_id, stats)
