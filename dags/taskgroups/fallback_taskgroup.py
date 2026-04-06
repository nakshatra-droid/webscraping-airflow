from airflow.utils.task_group import TaskGroup

from tasks.fallback_tasks import (
    collect_urls,
    insert_metadata,
    scrape_products,
    update_data,
    validate_products,
)


def fallback_taskgroup(source):
    with TaskGroup(group_id="fallback_scraper") as tg:
        run_id = insert_metadata()

        activity_batch = collect_urls(source)

        products = scrape_products(source, activity_batch)

        stats = validate_products(source, products)

        update_data(metadata_run_id=run_id, source=source, stats=stats)

        run_id >> activity_batch >> products >> stats

    return tg
