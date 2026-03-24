import random
import re
import asyncio
import uuid
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

from core.constants.constants_values import ActivityTypes, AmazonConstants
from core.utils.amazon_playwright_helpers import AmazonPlaywrightHelpers
from core.data_controllers.amazon_db_helpers import AmazonDBHelpers

load_dotenv()

CATEGORY_URL = AmazonConstants.CATEGORY_URL
NUMBER_OF_URLS = AmazonConstants.NUMBER_OF_URLS
BASE_URL = AmazonConstants.BASE_URL
SOURCE = AmazonConstants.SOURCE
SINGLE_URL = AmazonConstants.SINGLE_URL
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
BATCH_SIZE = AmazonConstants.BATCH_SIZE
NEXT_BTN_SEL = AmazonConstants.NEXT_BTN_SEL


class AmazonScraping:
    """Consolidated Amazon scraping functionality with static helper methods."""

    @staticmethod
    async def delay(min_s=0.8, max_s=2.2):
        await asyncio.sleep(random.uniform(min_s, max_s))

    @staticmethod
    async def safe_text(locator, timeout=3000) -> str:
        try:
            if await locator.count() == 0:
                return "N/A"
            return (await locator.first.inner_text(timeout=timeout)).strip() or "N/A"
        except Exception:
            return "N/A"

    @staticmethod
    async def safe_attr(locator, attr: str, timeout=3000) -> str:
        try:
            if await locator.count() == 0:
                return "N/A"
            val = await locator.first.get_attribute(attr, timeout=timeout)
            return (val or "N/A").strip()
        except Exception:
            return "N/A"

    @staticmethod
    def clean_price(raw: str) -> str:
        digits = re.sub(r"[^\d,.]", "", raw)
        return f"₹{digits}" if digits else "N/A"

    @staticmethod
    def _clean_text(raw: str | None) -> str:
        if not raw:
            return ""
        return re.sub(r"[\u200e\u200f\ufeff]", "", raw).strip()

    @staticmethod
    def _normalise_key(raw: str) -> str:
        lowered = AmazonScraping._clean_text(raw).lower()
        lowered = re.sub(r"[^a-z0-9 ]+", " ", lowered)
        return " ".join(lowered.split())

    @staticmethod
    def parse_price_value(raw: str | None) -> float | None:
        if not raw or raw == "N/A":
            return None
        m = re.search(r"[\d,]+", raw)
        if not m:
            return None
        try:
            return float(m.group(0).replace(",", ""))
        except ValueError:
            return None

    @staticmethod
    def parse_discount_value(raw: str | None) -> int | None:
        if not raw or raw == "N/A":
            return None
        m = re.search(r"(\d+)", raw)
        return int(m.group(1)) if m else None

    @staticmethod
    def parse_rating_value(raw: str | None) -> float | None:
        if not raw or raw == "N/A":
            return None
        m = re.search(r"(\d+(?:\.\d+)?)", raw)
        if not m:
            return None
        try:
            return round(float(m.group(1)), 1)
        except ValueError:
            return None

    @staticmethod
    def parse_review_count_value(raw: str | None) -> int | None:
        if not raw or raw == "N/A":
            return None
        m = re.search(r"[\d,]+", raw)
        if not m:
            return None
        try:
            return int(m.group(0).replace(",", ""))
        except ValueError:
            return None

    @staticmethod
    def parse_iso_datetime(raw: str | None) -> datetime | None:
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is not None:
                return dt.astimezone(UTC).replace(tzinfo=None)
            return dt
        except ValueError:
            return None

    @staticmethod
    def extract_model_number(specs: dict) -> str | None:
        # Check both old and new key formats
        cleaned = AmazonScraping._clean_text(
            str(specs.get("Model Number") or specs.get("Item model number") or "")
        )
        return cleaned or None

    @staticmethod
    def clean_store_brand(raw_brand: str | None) -> str | None:
        brand = AmazonScraping._clean_text(raw_brand)
        if brand and brand != "N/A":
            brand = re.sub(r"^Visit the\s+", "", brand, flags=re.IGNORECASE)
            brand = re.sub(r"\s+Store$", "", brand, flags=re.IGNORECASE).strip()
            if brand:
                return brand
        return None

    @staticmethod
    def first_spec_value(specs_lower: dict, *keys: str) -> str | None:
        for key in keys:
            value = AmazonScraping._clean_text(specs_lower.get(key) or "")
            if value:
                return value
        return None

    @staticmethod
    def normalise_brand(raw_brand: str | None, specs_lower: dict) -> str | None:
        spec_brand = AmazonScraping.first_spec_value(specs_lower, "brand")
        return spec_brand or AmazonScraping.clean_store_brand(raw_brand)

    @staticmethod
    def normalise_product(raw: dict) -> dict | None:
        specs_raw = raw.get("specifications") or {}
        specs_lower = {
            AmazonScraping._normalise_key(k): AmazonScraping._clean_text(str(v))
            for k, v in specs_raw.items()
            if AmazonScraping._clean_text(str(k))
        }

        model_number = AmazonScraping.extract_model_number(specs_raw)

        processor_parts = [
            AmazonScraping.first_spec_value(specs_lower, "processor brand") or "",
            AmazonScraping.first_spec_value(specs_lower, "processor type") or "",
        ]
        processor = " ".join([p for p in processor_parts if p]) or None

        image_list = raw.get("images") or []

        return {
            "model_number": model_number,
            "brand": AmazonScraping.normalise_brand(raw.get("brand"), specs_lower),
            "series": AmazonScraping.first_spec_value(
                specs_lower, "model name"
            ),
            "processor": processor,
            "ram": AmazonScraping.first_spec_value(
                specs_lower, "ram memory installed", "maximum memory supported"
            ),
            "storage": AmazonScraping.first_spec_value(specs_lower, "hard drive size"),
            "screen_size": AmazonScraping.first_spec_value(
                specs_lower, "screen size", "standing screen display size"
            ),
            "graphic_processor": AmazonScraping.first_spec_value(
                specs_lower, "graphics co processor", "graphics coprocessor"
            ),
            "colour": AmazonScraping.first_spec_value(specs_lower, "colour"),
            "price": AmazonScraping.parse_price_value(raw.get("price")),
            "discount": AmazonScraping.parse_discount_value(raw.get("discount")),
            "rating": AmazonScraping.parse_rating_value(raw.get("rating")),
            "review_count": AmazonScraping.parse_review_count_value(
                raw.get("review_count")
            ),
            "url": raw.get("url", ""),
            "image_url": image_list[0] if image_list else None,
            "scraped_at": AmazonScraping.parse_iso_datetime(raw.get("scraped_at")),
        }

    @staticmethod
    def has_required_fields(raw: dict) -> tuple[bool, list[str]]:
        missing = []
        for field in ("model_number", "brand", "series", "processor", "ram", "storage"):
            if not raw.get(field):
                missing.append(field)
        return (len(missing) == 0, missing)

    @staticmethod
    def extract_asin_from_href(href: str) -> str | None:
        patterns = [
            r"/dp/([A-Z0-9]{10})",
            r"/gp/product/([A-Z0-9]{10})",
            r"/product/([A-Z0-9]{10})",
        ]
        for pattern in patterns:
            match = re.search(pattern, href)
            if match:
                return match.group(1)
        return None

    @staticmethod
    async def collect_listing_hrefs_from_dom(page) -> list[str]:
        """Collect product-like hrefs from listing DOM (primary strategy)."""
        hrefs = await page.evaluate(
            """() => {
                const slots = document.querySelectorAll("div.s-main-slot a[href]");
                const all = slots.length ? slots : document.querySelectorAll("a[href]");
                return Array.from(all).map((a) => a.getAttribute("href") || "");
            }"""
        )
        return [h for h in hrefs if h and ("/dp/" in h or "/gp/product/" in h)]

    @staticmethod
    async def collect_product_urls(
        page, already_scraped: set[str] | None = None
    ) -> list[str]:
        """
        Crawl category listing pages until NUMBER_OF_URLS unique URLs are collected.
        """
        print(f"\n{'=' * 55}")
        print(f"  STEP 1 — Collecting URLs  (target: {NUMBER_OF_URLS})")
        print(f"{'=' * 55}")

        if already_scraped is None:
            already_scraped = set()

        print("\n  Loading category page...")
        try:
            await page.goto(CATEGORY_URL, wait_until="networkidle", timeout=10000)
        except PWTimeout:
            print("     (networkidle timed out, continuing with what loaded)")

        # Ensure HTML is at least parsed and listing container has a chance to render.
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
            await page.locator("div.s-main-slot").first.wait_for(
                state="attached", timeout=10000
            )
        except Exception:
            pass

        await asyncio.sleep(1.5)
        await AmazonPlaywrightHelpers.handle_captcha(page)
        await AmazonPlaywrightHelpers.close_any_popups(page)

        seen_asins = set()
        all_urls = []
        skipped_count = 0

        page_num = 1
        while len(all_urls) < NUMBER_OF_URLS:
            print(f"\n  📄 Page {page_num}...")

            await AmazonPlaywrightHelpers.handle_captcha(page)

            extracted_hrefs = await AmazonScraping.collect_listing_hrefs_from_dom(page)

            if not extracted_hrefs:
                print("     ⚠  No product links found, retrying page load once...")
                try:
                    await page.reload(wait_until="domcontentloaded", timeout=15000)
                except Exception:
                    pass
                await asyncio.sleep(1.2)
                extracted_hrefs = await AmazonScraping.collect_listing_hrefs_from_dom(
                    page
                )

            if not extracted_hrefs:
                print(f"  ✗ No product links on page {page_num} — stopping")
                await AmazonPlaywrightHelpers.handle_captcha(page)
                break

            new_on_page = 0
            for href in extracted_hrefs:
                asin = AmazonScraping.extract_asin_from_href(href)
                if asin:
                    if asin not in seen_asins:
                        seen_asins.add(asin)
                        clean_url = f"{BASE_URL}/dp/{asin}?th=1"
                        if clean_url in already_scraped:
                            skipped_count += 1
                            continue
                        all_urls.append(clean_url)
                        new_on_page += 1
                        if len(all_urls) >= NUMBER_OF_URLS:
                            break

            print(f"     +{new_on_page} new URLs  (total: {len(all_urls)})")

            if len(all_urls) >= NUMBER_OF_URLS:
                print("  ✓ Reached NUMBER_OF_URLS target")
                break

            next_btn = page.locator(NEXT_BTN_SEL).first
            try:
                if not await next_btn.is_visible(timeout=3000):
                    print("  ⚑ No Next button — end of results")
                    break
            except Exception:
                print("  ⚑ Next button not found — end of results")
                break

            active_selector = "div.s-main-slot a[href*='/dp/'], div.s-main-slot a[href*='/gp/product/']"

            first_href_before = (
                await page.locator(active_selector).first.get_attribute("href") or ""
            )

            await AmazonPlaywrightHelpers.human_scroll(page)
            await AmazonPlaywrightHelpers.move_mouse_randomly(page)
            wait_sec = random.uniform(1.5, 3.5)
            print(f"     Waiting {wait_sec:.1f}s then clicking Next...")
            await asyncio.sleep(wait_sec)

            await next_btn.scroll_into_view_if_needed()
            await next_btn.click()

            try:
                await page.wait_for_function(
                    f"""() => {{
                        const first = document.querySelector({repr(active_selector)});
                        return first && first.getAttribute("href") !== {repr(first_href_before)};
                    }}""",
                    timeout=15000,
                )
                print("     ✓ New page content detected")
            except Exception:
                print("     ⚠  Content did not change after Next click")
                first_href_after = (
                    await page.locator(active_selector).first.get_attribute("href")
                    or ""
                )
                if first_href_after == first_href_before:
                    print("     ✗ Same content as before — stopping")
                    break

            await asyncio.sleep(0.8)

            if await AmazonPlaywrightHelpers.handle_captcha(page):
                await asyncio.sleep(2)

            page_num += 1

        print(
            f"\n  ✅ Total unique product URLs: {len(all_urls)}"
            f"  (skipped already-scraped: {skipped_count})"
        )
        return all_urls

    @staticmethod
    async def open_product_page(page, url: str):
        """Navigate an existing page object to a product URL."""

        async def route_handler(route):
            blocked = [
                "doubleclick",
                "googlesyndication",
                "amazon-adsystem",
                "google-analytics",
            ]
            if any(x in route.request.url for x in blocked):
                await route.abort()
            else:
                await route.continue_()

        try:
            await page.route("**/*", route_handler)
        except Exception:
            pass

        print("\n  🌐 Loading product page...")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=35000)
        except PWTimeout:
            print("     domcontentloaded timed out — continuing anyway")

        try:
            await page.wait_for_selector(
                AmazonConstants.PRODUCT_TITLE_SEL, timeout=15000
            )
        except PWTimeout:
            print("     ⚠  Product title not found — page may be blocked or slow")

        await AmazonPlaywrightHelpers.handle_captcha(page)
        await AmazonPlaywrightHelpers.close_any_popups(page)
        await AmazonScraping.delay(1.5, 2.5)
        await AmazonPlaywrightHelpers.human_scroll(page)
        await AmazonScraping.delay(0.8, 1.5)

    @staticmethod
    async def extract(page) -> dict:
        print("    🔍 Extracting product data...")

        title = await AmazonScraping.safe_text(
            page.locator(AmazonConstants.PRODUCT_TITLE_SEL)
        )
        asin = await AmazonScraping.safe_attr(
            page.locator(AmazonConstants.ASIN_SEL), "value"
        )
        if asin == "N/A":
            m = re.search(r"/dp/([A-Z0-9]{10})", page.url)
            asin = m.group(1) if m else "N/A"

        brand = await AmazonScraping.safe_text(page.locator(AmazonConstants.BRAND_SEL))

        price_whole = await AmazonScraping.safe_text(
            page.locator(AmazonConstants.PRICE_WHOLE_SEL).first
        )
        price_frac = await AmazonScraping.safe_text(
            page.locator(AmazonConstants.PRICE_FRAC_SEL).first
        )
        if price_whole != "N/A":
            price = AmazonScraping.clean_price(f"{price_whole}.{price_frac}")
        else:
            price = AmazonScraping.clean_price(
                await AmazonScraping.safe_text(page.locator(AmazonConstants.PRICE_SEL))
            )

        mrp = AmazonScraping.clean_price(
            await AmazonScraping.safe_text(page.locator(AmazonConstants.MRP_SEL).first)
        )

        discount = await AmazonScraping.safe_text(
            page.locator(AmazonConstants.DISCOUNT_SEL).first
        )

        rating = await AmazonScraping.safe_text(
            page.locator(AmazonConstants.RATING_SEL)
        )
        if rating == "N/A":
            rating = await AmazonScraping.safe_text(
                page.locator(AmazonConstants.RATING_FIRST_SEL).first
            )

        review_count = await AmazonScraping.safe_text(
            page.locator(AmazonConstants.REVIEW_SEL)
        )
        if review_count == "N/A":
            review_count = await AmazonScraping.safe_text(
                page.locator(AmazonConstants.REVIEW_FIRST_SEL)
            )

        availability = await AmazonScraping.safe_text(
            page.locator(AmazonConstants.AVAILABILITY_SEL).first
        )
        sold_by = await AmazonScraping.safe_text(
            page.locator(AmazonConstants.SOLD_BY_SEL)
        )
        ships_from = await AmazonScraping.safe_text(
            page.locator(AmazonConstants.SHIPS_FROM_SEL).first
        )

        images = []
        main_src = await AmazonScraping.safe_attr(
            page.locator(AmazonConstants.MAIN_SRC_IMG_SEL), "src"
        )
        if main_src != "N/A":
            images.append(main_src)
        thumbs = page.locator(AmazonConstants.THUMBNAILS_SEL)
        for i in range(min(await thumbs.count(), 8)):
            src = await thumbs.nth(i).get_attribute("src") or ""
            hires = re.sub(r"\._[A-Z0-9_,]+_\.", ".", src)
            if hires and hires not in images:
                images.append(hires)

        feat_loc = page.locator(AmazonConstants.FEATURES_SEL)
        features = []
        for i in range(await feat_loc.count()):
            txt = (await feat_loc.nth(i).inner_text()).strip()
            if txt and len(txt) > 5:
                features.append(txt)

        specs = {}

        async def harvest_table(css: str):
            rows = page.locator(f"{css} tr")
            for i in range(await rows.count()):
                row = rows.nth(i)
                th = row.locator("th")
                td = row.locator("td")
                if await th.count() and await td.count():
                    k = (await th.inner_text()).strip()
                    v = (await td.last.inner_text()).strip()
                    if k and v and k != v:
                        specs[k] = v

        await harvest_table(AmazonConstants.TECH_SPEC_SECTION1)
        await harvest_table(AmazonConstants.TECH_SPEC_SECTION2)
        await harvest_table(AmazonConstants.PRODUCT_DETAILS_SECTION1)
        await harvest_table(AmazonConstants.PRODUCT_DETAIL_TABLE)
        await harvest_table(AmazonConstants.TECHNICAL_SPEC_SECTION)

        if not specs:
            items = page.locator(AmazonConstants.ITEMS)
            for i in range(await items.count()):
                text = (await items.nth(i).inner_text()).strip()
                if ":" in text:
                    k, _, v = text.partition(":")
                    specs[k.strip()] = v.strip()

        about = await AmazonScraping.safe_text(
            page.locator(AmazonConstants.PRODUCT_DESCRIPTION)
        )

        variants = {}
        var_loc = page.locator(AmazonConstants.VARIANTS)
        for i in range(await var_loc.count()):
            txt = (await var_loc.nth(i).inner_text()).strip()
            if txt:
                variants[f"option_{i + 1}"] = txt

        return {
            "scraped_at": AmazonDBHelpers.utcnow_naive().isoformat(),
            "url": page.url,
            "asin": asin,
            "title": title,
            "brand": brand,
            "price": price,
            "mrp": mrp,
            "discount": discount,
            "rating": rating,
            "review_count": review_count,
            "availability": availability,
            "sold_by": sold_by,
            "ships_from": ships_from,
            "images": images,
            "features": features,
            "about": about[:800] if about != "N/A" else "N/A",
            "specifications": specs,
            "variants": variants,
        }

    @staticmethod
    def insert_metadata() -> str:
        return str(AmazonDBHelpers.create_scraping_run())

    @staticmethod
    def fetch_existing_urls() -> list[str]:
        return sorted(list(AmazonDBHelpers.fetch_scraped_urls()))

    @staticmethod
    def collect_urls(existing_urls: list[str] | None = None) -> list[str]:
        async def _collect() -> list[str]:
            async with async_playwright() as pw:
                browser, ctx = await AmazonPlaywrightHelpers.make_context(pw)
                page = await ctx.new_page()
                try:
                    return await AmazonScraping.collect_product_urls(
                        page, set(existing_urls or [])
                    )
                finally:
                    await ctx.close()
                    await browser.close()

        return asyncio.run(_collect())

    @staticmethod
    def scrape_products(urls: list[str]) -> list[dict]:
        async def _scrape() -> list[dict]:
            if not urls:
                return []

            scraped: list[dict] = []
            async with async_playwright() as pw:
                browser, ctx = await AmazonPlaywrightHelpers.make_context(pw)
                page = await ctx.new_page()
                try:
                    for url in urls:
                        try:
                            await AmazonScraping.open_product_page(page, url)
                            raw = await AmazonScraping.extract(page)
                            scraped.append(raw)
                        except Exception as exc:
                            scraped.append(
                                {
                                    "url": url,
                                    "_error": str(exc),
                                }
                            )
                finally:
                    await ctx.close()
                    await browser.close()

            return scraped

        return asyncio.run(_scrape())

    @staticmethod
    def validate_products(products: list[dict]) -> list[list[dict]]:
        valid: list[dict] = []
        invalid: list[dict] = []

        for raw in products or []:
            if raw.get("_error"):
                invalid.append(
                    {
                        "url": raw.get("url", ""),
                        "reason": ActivityTypes.PRODUCT_NOT_FOUND,
                        "product_data": None,
                    }
                )
                continue

            normalised = AmazonScraping.normalise_product(raw)
            ok, missing = AmazonScraping.has_required_fields(normalised)
            if ok:
                valid.append(normalised)
            else:
                invalid.append(
                    {
                        "url": normalised.get("url", raw.get("url", "")),
                        "reason": ActivityTypes.FIELD_MISSING,
                        "product_data": normalised,
                    }
                )

        return [valid, invalid]

    @staticmethod
    def update_metadata(run_id: str, stats: list[list[dict]]) -> None:
        valid = stats[0] if stats else []
        invalid = stats[1] if stats and len(stats) > 1 else []

        run_uuid = uuid.UUID(run_id)
        hook = AmazonDBHelpers.get_hook()
        conn = hook.get_conn()
        cur = conn.cursor()

        try:
            valid_count = 0
            invalid_count = 0

            for row in valid:
                try:
                    product_id = AmazonDBHelpers.upsert_product(cur, row)
                    AmazonDBHelpers.upsert_product_details(
                        cur, product_id, run_uuid, row
                    )
                    valid_count += 1
                except Exception as exc:
                    invalid_count += 1
                    AmazonDBHelpers.log_activity(
                        cur,
                        run_uuid,
                        ActivityTypes.PRODUCT_NOT_FOUND,
                        row.get("url", ""),
                        {"error": str(exc), "product_data": row},
                    )

            for row in invalid:
                invalid_count += 1
                AmazonDBHelpers.log_activity(
                    cur,
                    run_uuid,
                    row.get("reason", ActivityTypes.FIELD_MISSING),
                    row.get("url", ""),
                    row.get("product_data"),
                )

            conn.commit()

            attempted = valid_count + invalid_count
            AmazonDBHelpers.finalise_scraping_run(
                run_uuid,
                attempted=attempted,
                valid=valid_count,
                invalid=invalid_count,
            )
        finally:
            cur.close()
            conn.close()
