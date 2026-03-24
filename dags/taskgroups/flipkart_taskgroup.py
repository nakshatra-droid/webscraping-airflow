from airflow.utils.task_group import TaskGroup

from tasks.flipkart_tasks import (
    insert_metadata,
    fetch_existing_urls,
    collect_urls,
    scrape_products,
    validate_products,
    update_metadata,
)


def flipkart_taskgroup():

    with TaskGroup(group_id="flipkart_scraper") as tg:
        run_id = insert_metadata()

        existing = fetch_existing_urls()

        urls = collect_urls(existing)

        products = scrape_products(urls)

        stats = validate_products(products)

        update_metadata(metadata_run_id=run_id, stats=stats)

        run_id >> existing >> urls >> products >> stats

    return tg
