import uuid
from datetime import UTC, datetime

from airflow.providers.postgres.hooks.postgres import PostgresHook

from config.config_values import ConfigValues
from core.constants.constants_values import AmazonConstants, FlipkartConstants
from core.utils.fallback_queries import (
    DELETE_ACTIVITY_BY_ID,
    FETCH_FALLBACK_ACTIVITY_BATCH,
    INSERT_SCRAPING_RUN,
    UPDATE_ACTIVITY_RETRY,
    UPDATE_SCRAPING_RUN,
    UPSERT_PRODUCT,
    UPSERT_PRODUCT_DETAILS_TEMPLATE,
)

PRODUCT_DETAILS_TABLE = ConfigValues.PRODUCT_DETAILS_TABLE
POSTGRES_CONN_ID = ConfigValues.POSTGRES_CONN_ID


class FallbackDBHelpers:
    @staticmethod
    def utcnow_naive() -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    @staticmethod
    def normalise_source(source: str | None) -> str:
        source_val = (source or AmazonConstants.SOURCE).upper()
        if source_val not in (AmazonConstants.SOURCE, FlipkartConstants.SOURCE):
            return AmazonConstants.SOURCE
        return source_val

    @staticmethod
    def get_source_like(source: str) -> str:
        source_val = FallbackDBHelpers.normalise_source(source)
        if source_val == FlipkartConstants.SOURCE:
            return "%flipkart%"
        return "%amazon%"

    @staticmethod
    def get_hook() -> PostgresHook:
        return PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    @staticmethod
    def create_scraping_run() -> uuid.UUID:
        run_id = uuid.uuid4()
        now = FallbackDBHelpers.utcnow_naive()
        hook = FallbackDBHelpers.get_hook()
        hook.run(INSERT_SCRAPING_RUN, parameters=(str(run_id), now, now, now))
        print(f" Fallback scraping run created  run_id={run_id}")
        return run_id

    @staticmethod
    def finalise_scraping_run(
        run_id: uuid.UUID,
        attempted: int,
        valid: int,
        invalid: int,
    ):
        now = FallbackDBHelpers.utcnow_naive()
        hook = FallbackDBHelpers.get_hook()
        hook.run(
            UPDATE_SCRAPING_RUN,
            parameters=(attempted, valid, invalid, now, now, str(run_id)),
        )

    @staticmethod
    def fetch_and_mark_activity_batch(source: str, limit: int) -> list[dict]:
        source_like = FallbackDBHelpers.get_source_like(source)
        hook = FallbackDBHelpers.get_hook()
        conn = hook.get_conn()
        cur = conn.cursor()

        rows_out: list[dict] = []
        now = FallbackDBHelpers.utcnow_naive()

        try:
            cur.execute(FETCH_FALLBACK_ACTIVITY_BATCH, (source_like, limit))
            rows = cur.fetchall() or []

            if not rows:
                conn.commit()
                return []

            for activity_id, product_url, retry_count in rows:
                cur.execute(UPDATE_ACTIVITY_RETRY, (now, str(activity_id)))
                rows_out.append(
                    {
                        "activity_id": str(activity_id),
                        "url": product_url,
                        "retry_count": int(retry_count or 0) + 1,
                    }
                )

            conn.commit()
            print(
                f" Fallback batch fetched for {source} — {len(rows_out)} URLs "
                f"(retries incremented)"
            )
            return rows_out
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def upsert_product(cur, normalised: dict) -> uuid.UUID:
        now = FallbackDBHelpers.utcnow_naive()
        cur.execute(
            UPSERT_PRODUCT,
            (
                normalised["model_number"],
                normalised.get("brand"),
                normalised.get("series"),
                normalised.get("processor"),
                normalised.get("ram"),
                normalised.get("storage"),
                normalised.get("screen_size"),
                normalised.get("graphic_processor"),
                normalised.get("colour"),
                now,
                now,
            ),
        )
        return cur.fetchone()[0]

    @staticmethod
    def upsert_product_details(
        cur,
        product_id: uuid.UUID,
        run_id: uuid.UUID,
        source: str,
        normalised: dict,
    ):
        now = FallbackDBHelpers.utcnow_naive()
        query = UPSERT_PRODUCT_DETAILS_TEMPLATE.format(
            product_details_table=PRODUCT_DETAILS_TABLE
        )
        cur.execute(
            query,
            (
                str(product_id),
                FallbackDBHelpers.normalise_source(source),
                str(run_id),
                normalised.get("price"),
                normalised.get("discount"),
                normalised.get("rating"),
                normalised.get("review_count"),
                normalised["url"],
                normalised.get("image_url"),
                normalised.get("scraped_at") or now,
                now,
            ),
        )

    @staticmethod
    def delete_activity_by_id(cur, activity_id: str):
        cur.execute(DELETE_ACTIVITY_BY_ID, (activity_id,))
