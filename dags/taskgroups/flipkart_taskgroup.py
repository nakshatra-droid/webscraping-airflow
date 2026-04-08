from airflow.decorators import task_group

from tasks.flipkart_tasks import (
    insert_metadata,
    fetch_existing_urls,
    collect_urls,
    scrape_products,
    validate_products,
    update_data,
)


@task_group(group_id="flipkart_scraper")
def flipkart_taskgroup():
    run_id = insert_metadata()

    existing = fetch_existing_urls()

    urls = collect_urls(existing)

    products = scrape_products(urls)

    stats = validate_products(products)

    update_data(metadata_run_id=run_id, stats=stats)

    run_id >> existing >> urls >> products >> stats
