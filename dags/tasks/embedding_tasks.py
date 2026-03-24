from airflow.decorators import task

from core.embeddings.embedding_pipeline import EmbeddingPipeline


@task
def insert_embedding_metadata():

    return EmbeddingPipeline.insert_embedding_metadata()


@task
def fetch_pending_products():

    return EmbeddingPipeline.fetch_pending_products()


@task
def build_embedding_texts(products):

    return EmbeddingPipeline.build_embedding_texts(products)


@task
def generate_embeddings(texts):

    return EmbeddingPipeline.generate_embeddings(texts)


@task
def insert_embeddings(rows, metadata_run_id):

    return EmbeddingPipeline.insert_embeddings(rows, metadata_run_id)


@task
def update_product_status(product_ids):

    return EmbeddingPipeline.update_product_status(product_ids)


@task
def update_metadata(metadata_run_id, total_count):

    EmbeddingPipeline.update_metadata(metadata_run_id, total_count)
