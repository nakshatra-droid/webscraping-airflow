import json
import uuid
from datetime import UTC, datetime

from airflow.providers.postgres.hooks.postgres import PostgresHook

from config.config_values import ConfigValues
from core.constants.constants_values import AmazonConstants
from core.utils.amazon_queries import (
    FETCH_ACTIVITY_URLS,
    FETCH_PRODUCT_URLS_TEMPLATE,
    INSERT_ACTIVITY_LOG,
    INSERT_SCRAPING_RUN,
    UPDATE_SCRAPING_RUN,
    UPSERT_PRODUCT,
    UPSERT_PRODUCT_DETAILS_TEMPLATE,
)

PRODUCT_DETAILS_TABLE = ConfigValues.PRODUCT_DETAILS_TABLE
POSTGRES_CONN_ID = ConfigValues.POSTGRES_CONN_ID
SOURCE = AmazonConstants.SOURCE


class AmazonDBHelpers:
    @staticmethod
    def utcnow_naive() -> datetime:
        """Return UTC time as naive datetime for TIMESTAMP WITHOUT TIME ZONE columns."""
        return datetime.now(UTC).replace(tzinfo=None)

    @staticmethod
    def _json_default(obj):
        """Allow JSON serialization for non-primitive types in activity payloads."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, uuid.UUID):
            return str(obj)
        raise TypeError(
            f"Object of type {obj.__class__.__name__} is not JSON serializable"
        )

    @staticmethod
    def get_hook() -> PostgresHook:
        return PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    @staticmethod
    def create_scraping_run() -> uuid.UUID:
        """Create one scraping_metadata row and return run_id."""
        run_id = uuid.uuid4()
        now = AmazonDBHelpers.utcnow_naive()
        hook = AmazonDBHelpers.get_hook()
        hook.run(INSERT_SCRAPING_RUN, parameters=(str(run_id), now, now, now))
        print(f"  📝 Scraping run created  run_id={run_id}")
        return run_id

    @staticmethod
    def finalise_scraping_run(
        run_id: uuid.UUID,
        attempted: int,
        valid: int,
        invalid: int,
    ):
        """Update final counters and end_time in scraping_metadata."""
        now = AmazonDBHelpers.utcnow_naive()
        hook = AmazonDBHelpers.get_hook()
        hook.run(
            UPDATE_SCRAPING_RUN,
            parameters=(attempted, valid, invalid, now, now, str(run_id)),
        )

    @staticmethod
    def upsert_product(cur, normalised: dict) -> uuid.UUID:
        """Upsert into products and return product_id."""
        now = AmazonDBHelpers.utcnow_naive()
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
        normalised: dict,
    ):
        """Upsert listing/source-specific details."""
        now = AmazonDBHelpers.utcnow_naive()
        query = UPSERT_PRODUCT_DETAILS_TEMPLATE.format(
            product_details_table=PRODUCT_DETAILS_TABLE
        )
        cur.execute(
            query,
            (
                str(product_id),
                SOURCE,
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
    def log_activity(
        cur,
        run_id: uuid.UUID,
        activity_type: str,
        url: str,
        product_data: dict | None = None,
    ):
        """Write one row to activity_logs."""
        now = AmazonDBHelpers.utcnow_naive()
        cur.execute(
            INSERT_ACTIVITY_LOG,
            (
                str(run_id),
                activity_type,
                json.dumps(product_data, default=AmazonDBHelpers._json_default)
                if product_data is not None
                else None,
                url,
                0,
                False,
                now,
                now,
            ),
        )

    @staticmethod
    def fetch_scraped_urls() -> set[str]:
        """Return merged URLs already seen in product_details and activity_logs."""
        hook = AmazonDBHelpers.get_hook()
        product_query = FETCH_PRODUCT_URLS_TEMPLATE.format(
            product_details_table=PRODUCT_DETAILS_TABLE
        )
        product_rows = hook.get_records(product_query, parameters=(SOURCE,))
        activity_rows = hook.get_records(FETCH_ACTIVITY_URLS)

        product_urls = {row[0] for row in product_rows if row[0]}
        activity_urls = {row[0] for row in activity_rows if row[0]}
        merged_urls = product_urls | activity_urls

        print(
            f"  📋 Already seen URLs ({SOURCE}) — "
            f"products: {len(product_urls)}, activity_logs: {len(activity_urls)}, "
            f"merged: {len(merged_urls)}"
        )
        return merged_urls

    @staticmethod
    def flush_activity_buffer(cur, activity_buffer: list[dict]) -> bool:
        """Flush buffered activity logs in one batch insert."""
        if not activity_buffer:
            return True

        now = AmazonDBHelpers.utcnow_naive()
        rows = [
            (
                str(item["run_id"]),
                item["activity_type"],
                json.dumps(
                    item.get("product_data"), default=AmazonDBHelpers._json_default
                )
                if item.get("product_data") is not None
                else None,
                item["url"],
                0,
                False,
                now,
                now,
            )
            for item in activity_buffer
        ]

        try:
            cur.executemany(INSERT_ACTIVITY_LOG, rows)
            print(f"  ✅ Flushed activity batch: {len(activity_buffer)}")
            activity_buffer.clear()
            return True
        except Exception as exc:
            print(
                f"  ✗ Activity batch flush failed ({len(activity_buffer)} kept in buffer): {exc}"
            )
            return False

    @staticmethod
    def flush_product_buffer(
        cur,
        run_id: uuid.UUID,
        product_buffer: list[dict],
    ) -> int:
        """Flush buffered valid products and details in one DB transaction."""
        if not product_buffer:
            return 0

        saved_count = 0
        query = UPSERT_PRODUCT_DETAILS_TEMPLATE.format(
            product_details_table=PRODUCT_DETAILS_TABLE
        )
        try:
            for normalised in product_buffer:
                product_id = AmazonDBHelpers.upsert_product(cur, normalised)
                now = AmazonDBHelpers.utcnow_naive()
                cur.execute(
                    query,
                    (
                        str(product_id),
                        SOURCE,
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
                saved_count += 1
            print(f"  ✅ Flushed product batch: {saved_count}")
            product_buffer.clear()
            return saved_count
        except Exception as exc:
            print(
                f"  ✗ Product batch flush failed ({len(product_buffer)} kept in buffer): {exc}"
            )
            return 0
