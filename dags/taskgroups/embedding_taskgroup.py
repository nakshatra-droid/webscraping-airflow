from airflow.utils.task_group import TaskGroup

from tasks.embedding_tasks import (
    insert_embedding_metadata,
    fetch_pending_products,
    build_embedding_texts,
    generate_embeddings,
    insert_embeddings,
    update_product_status,
    update_metadata,
)


def embedding_taskgroup(group_id):

    with TaskGroup(group_id=group_id) as tg:
        run_id = insert_embedding_metadata()

        products = fetch_pending_products()

        texts = build_embedding_texts(products)

        embeddings = generate_embeddings(texts)

        ids = insert_embeddings(embeddings, metadata_run_id=run_id)

        updated = update_product_status(ids)

        update_metadata(metadata_run_id=run_id, total_count=updated)

        run_id >> products >> texts >> embeddings >> ids >> updated

    return tg
