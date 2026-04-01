import uuid

from core.constants.constants_values import AmazonConstants, FlipkartConstants
from core.data_controllers.fallback_db_helpers import FallbackDBHelpers
from core.scraping.amazon_scraping import AmazonScraping
from core.scraping.flipkart_scraping import FlipkartScraping
from core.utils.fallback_validation import FallbackValidation


class FallbackScraping:
    @staticmethod
    def normalise_source(source: str | None) -> str:
        return FallbackDBHelpers.normalise_source(source)

    @staticmethod
    def source_batch_size(source: str) -> int:
        source_val = FallbackScraping.normalise_source(source)
        if source_val == FlipkartConstants.SOURCE:
            return FlipkartConstants.BATCH_SIZE
        return AmazonConstants.BATCH_SIZE

    @staticmethod
    def insert_metadata() -> str:
        return str(FallbackDBHelpers.create_scraping_run())

    @staticmethod
    def collect_urls(source: str | None = None) -> list[dict]:
        source_val = FallbackScraping.normalise_source(source)
        limit = FallbackScraping.source_batch_size(source_val)
        return FallbackDBHelpers.fetch_and_mark_activity_batch(source_val, limit)

    @staticmethod
    def scrape_products(source: str | None, activity_batch: list[dict]) -> list[dict]:
        source_val = FallbackScraping.normalise_source(source)
        if not activity_batch:
            return []

        urls = [row["url"] for row in activity_batch if row.get("url")]

        if source_val == FlipkartConstants.SOURCE:
            scraped = FlipkartScraping.scrape_products(urls)
        else:
            scraped = AmazonScraping.scrape_products(urls)

        indexed_by_url: dict[str, list[dict]] = {}
        for item in scraped:
            indexed_by_url.setdefault(item.get("url", ""), []).append(item)

        merged: list[dict] = []
        for row in activity_batch:
            current_url = row.get("url", "")
            candidates = indexed_by_url.get(current_url, [])
            if candidates:
                raw = candidates.pop(0)
                raw["activity_id"] = row.get("activity_id")
                merged.append(raw)
            else:
                merged.append(
                    {
                        "url": current_url,
                        "activity_id": row.get("activity_id"),
                        "_error": "Missing scraped result for URL",
                    }
                )

        return merged

    @staticmethod
    def validate_products(source: str | None, products: list[dict]) -> list[list[dict]]:
        source_val = FallbackScraping.normalise_source(source)
        return FallbackValidation.validate_products(source_val, products)

    @staticmethod
    def update_metadata(
        metadata_run_id: str, source: str | None, stats: list[list[dict]]
    ):
        source_val = FallbackScraping.normalise_source(source)

        valid = stats[0] if stats else []
        invalid = stats[1] if stats and len(stats) > 1 else []

        run_uuid = uuid.UUID(metadata_run_id)
        hook = FallbackDBHelpers.get_hook()
        conn = hook.get_conn()
        cur = conn.cursor()

        try:
            valid_count = 0
            invalid_count = 0

            for row in valid:
                try:
                    product_id = FallbackDBHelpers.upsert_product(cur, row)
                    FallbackDBHelpers.upsert_product_details(
                        cur, product_id, run_uuid, source_val, row
                    )
                    if row.get("activity_id"):
                        FallbackDBHelpers.delete_activity_by_id(
                            cur, row["activity_id"]
                        )
                    valid_count += 1
                except Exception as exc:
                    print(
                        f" Fallback upsert failed for URL {row.get('url', '')}: {exc}"
                    )
                    invalid_count += 1

            invalid_count += len(invalid)

            conn.commit()

            attempted = valid_count + invalid_count
            FallbackDBHelpers.finalise_scraping_run(
                run_uuid,
                attempted=attempted,
                valid=valid_count,
                invalid=invalid_count,
            )
            print(
                f" Fallback run finalised ({source_val}) — "
                f"attempted={attempted}, valid={valid_count}, invalid={invalid_count}"
            )
        finally:
            cur.close()
            conn.close()
