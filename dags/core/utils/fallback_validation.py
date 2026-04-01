from core.constants.constants_values import (
    ActivityTypes,
    AmazonConstants,
    FlipkartConstants,
)
from core.scraping.amazon_scraping import AmazonScraping
from core.scraping.flipkart_scraping import FlipkartScraping


class FallbackValidation:
    @staticmethod
    def normalise_source(source: str | None) -> str:
        source_val = (source or AmazonConstants.SOURCE).upper()
        if source_val not in (AmazonConstants.SOURCE, FlipkartConstants.SOURCE):
            return AmazonConstants.SOURCE
        return source_val

    @staticmethod
    def normalise_product(source: str, raw: dict) -> dict:
        if source == FlipkartConstants.SOURCE:
            return FlipkartScraping.normalise(raw)
        return AmazonScraping.normalise_product(raw)

    @staticmethod
    def has_required_fields(source: str, normalised: dict) -> tuple[bool, list[str]]:
        if source == FlipkartConstants.SOURCE:
            return FlipkartScraping.has_required_fields(normalised)
        return AmazonScraping.has_required_fields(normalised)

    @staticmethod
    def validate_products(source: str, products: list[dict]) -> list[list[dict]]:
        source_val = FallbackValidation.normalise_source(source)

        valid: list[dict] = []
        invalid: list[dict] = []

        for raw in products or []:
            activity_id = raw.get("activity_id")
            if raw.get("_error"):
                invalid.append(
                    {
                        "activity_id": activity_id,
                        "url": raw.get("url", ""),
                        "reason": ActivityTypes.PRODUCT_NOT_FOUND,
                        "product_data": None,
                    }
                )
                continue

            normalised = FallbackValidation.normalise_product(source_val, raw)
            ok, _missing = FallbackValidation.has_required_fields(
                source_val, normalised
            )

            if ok:
                normalised["activity_id"] = activity_id
                valid.append(normalised)
            else:
                invalid.append(
                    {
                        "activity_id": activity_id,
                        "url": normalised.get("url", raw.get("url", "")),
                        "reason": ActivityTypes.FIELD_MISSING,
                        "product_data": normalised,
                    }
                )

        return [valid, invalid]
