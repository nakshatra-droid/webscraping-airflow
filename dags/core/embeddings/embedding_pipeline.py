import uuid
import logging
from sentence_transformers import SentenceTransformer

from airflow.providers.postgres.hooks.postgres import PostgresHook

from core.utils.embedding_queries import *


POSTGRES_CONN_ID = "product_db"
BATCH_SIZE = 100
EMBED_MODEL = "sentence-transformers/multi-qa-mpnet-base-dot-v1"
EMBED_BATCH_SIZE = 64
logger = logging.getLogger(__name__)


class EmbeddingPipeline:
    @staticmethod
    def insert_embedding_metadata():

        hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

        run_id = str(uuid.uuid4())

        hook.run(INSERT_METADATA, parameters=(run_id,))

        return run_id

    @staticmethod
    def fetch_pending_products():

        hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

        records = hook.get_records(FETCH_PENDING_PRODUCTS, parameters=(BATCH_SIZE,))

        columns = [
            "id",
            "brand",
            "series",
            "processor",
            "ram",
            "storage",
            "graphic_processor",
            "colour",
        ]

        rows = [dict(zip(columns, r)) for r in records]

        return rows

    @staticmethod
    def build_embedding_texts(products):
        texts = []
        for p in products:
            parts = []

            if p["brand"] and p["series"]:
                parts.append(f"{p['brand']} {p['series']} laptop")
            elif p["brand"]:
                parts.append(f"{p['brand']} laptop")

            if p["processor"]:
                parts.append(f"powered by {p['processor']} processor")
            if p["ram"]:
                parts.append(f"with {p['ram']} RAM")
            if p["storage"]:
                parts.append(f"and {p['storage']} storage")
            if p["graphic_processor"]:
                parts.append(f"featuring {p['graphic_processor']} graphics")
            if p["colour"]:
                parts.append(f"in {p['colour']} colour")

            # Natural sentence — matches the style of user queries
            text = " ".join(parts) + "."
            texts.append({"id": p["id"], "text": text})

        return texts

    @staticmethod
    def generate_embeddings(text_rows):
        logger.info("Starting embedding generation for %d products", len(text_rows))

        if not text_rows:
            return []

        try:
            model = SentenceTransformer(EMBED_MODEL)
            logger.info(f"Loaded embedding model: {EMBED_MODEL}")
        except Exception as model_err:
            logger.error(f"Failed to load embedding model: {model_err}")
            raise model_err

        texts = [r["text"] for r in text_rows]
        ids = [r["id"] for r in text_rows]

        try:
            logger.info(
                f"Encoding {len(texts)} texts with batch size {EMBED_BATCH_SIZE}"
            )
            embeddings = model.encode(
                texts,
                batch_size=EMBED_BATCH_SIZE,
                show_progress_bar=True,
                normalize_embeddings=False,
            )
        except Exception as encode_err:
            logger.error(f"Encoding failed: {encode_err}")
            raise encode_err

        rows = []
        for product_id, embedding in zip(ids, embeddings):
            rows.append({"product_id": product_id, "embedding": embedding.tolist()})

        logger.info(
            "Completed embedding generation. Success=%d",
            len(rows),
        )

        return rows

    @staticmethod
    def insert_embeddings(rows, metadata_run_id):

        hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

        conn = hook.get_conn()
        cur = conn.cursor()

        product_ids = []

        for r in rows:
            cur.execute(
                INSERT_EMBEDDING,
                (
                    str(uuid.uuid4()),
                    r["product_id"],
                    metadata_run_id,
                    r["embedding"],
                ),
            )

            product_ids.append(r["product_id"])

        conn.commit()
        cur.close()

        return product_ids

    @staticmethod
    def update_product_status(product_ids):

        hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

        hook.run(UPDATE_PRODUCT_STATUS, parameters=(product_ids,))

        return len(product_ids)

    @staticmethod
    def update_metadata(run_id, total):

        hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

        hook.run(UPDATE_METADATA, parameters=(total, total, 0, run_id))
