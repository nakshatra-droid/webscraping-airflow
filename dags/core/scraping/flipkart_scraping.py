import asyncio
import random
import re
import uuid

from dotenv import load_dotenv
from playwright.async_api import async_playwright
from core.utils.flipkart_playwright_helpers import FlipkartPlaywrightHelpers
from core.data_controllers.flipkart_db_helpers import FlipkartDBHelpers
from config.config_values import ConfigValues
from core.constants.constants_values import FlipkartConstants, ActivityTypes

load_dotenv()

PRODUCT_DETAILS_TABLE = ConfigValues.PRODUCT_DETAILS_TABLE
BATCH_SIZE = FlipkartConstants.BATCH_SIZE
POSTGRES_CONN_ID = ConfigValues.POSTGRES_CONN_ID
CATEGORY_URL = FlipkartConstants.CATEGORY_URL
NUMBER_OF_URLS = FlipkartConstants.NUMBER_OF_URLS
BASE_URL = FlipkartConstants.BASE_URL
SOURCE = FlipkartConstants.SOURCE
PLAYWRIGHT_HEADLESS = True

STEALTH_SCRIPT = ConfigValues.STEALTH_SCRIPT


class FlipkartScraping:
    """Airflow-friendly static wrappers over the async Flipkart scraping business logic."""

    @staticmethod
    def parse_price(raw: str | None) -> float | None:
        """'62,841' or '62841' -> 62841.0  (strips rupee sign, commas, spaces)"""
        if not raw:
            return None
        cleaned = re.sub(r"[\u20b9,\s]", "", raw)
        try:
            return float(cleaned)
        except ValueError:
            return None

    @staticmethod
    def parse_discount(raw: str | None) -> int | None:
        """'36%' -> 36   (product_details.discount is Integer)"""
        if not raw:
            return None
        m = re.search(r"(\d+)", raw)
        return int(m.group(1)) if m else None

    @staticmethod
    def parse_rating(raw: str | None) -> float | None:
        """'4.5' -> 4.5   (product_details.rating is Numeric(2,1))"""
        if not raw:
            return None
        try:
            return round(float(raw.strip()), 1)
        except ValueError:
            return None

    @staticmethod
    def parse_review_count(raw: str | None) -> int | None:
        """
        '79'                          -> 79
        '3,389 Ratings & 234 Reviews' -> 3389
        Extracts the first number found in the string.
        """
        if not raw:
            return None
        m = re.search(r"[\d,]+", raw)
        if not m:
            return None
        try:
            return int(m.group().replace(",", ""))
        except ValueError:
            return None

    @staticmethod
    def extract_model_number(specs: dict) -> str | None:
        cleaned = (specs.get("Model Number") or "").strip()
        if cleaned:
            return cleaned

        for key, val in specs.items():
            if key.strip().lower() == "model number":
                cleaned = (val or "").strip()
                return cleaned if cleaned else None
        return None

    @staticmethod
    def build_processor(spec_lower: dict) -> str | None:
        """
        Combines: "Processor Brand" + "Processor Name" + "Processor Variant"
        e.g. "Intel" + "Core 7" + "150U" -> "Intel Core 7 150U"
        """
        brand = (spec_lower.get("processor brand") or "").strip()
        name = (spec_lower.get("processor name") or "").strip()
        variant = (spec_lower.get("processor variant") or "").strip()
        parts = [p for p in [brand, name, variant] if p]
        return " ".join(parts) if parts else None

    @staticmethod
    def has_required_fields(raw: dict) -> tuple[bool, list[str]]:
        missing = []
        for field in (
            "model_number",
            "brand",
            "series",
            "processor",
            "ram",
            "storage",
        ):
            if not raw.get(field):
                missing.append(field)
        return (len(missing) == 0, missing)

    @staticmethod
    def normalise(raw: dict) -> dict:
        """
        Convert raw scraper output into a clean dict that maps exactly to the
        products and product_details DB columns.

        Only fields that have a corresponding DB column are included.
        If model_number cannot be extracted, it is kept as None and validated later
        by has_required_fields().
        """
        specs = raw.get("specifications") or {}

        model_number = FlipkartScraping.extract_model_number(specs)

        spec_lower = {k.strip().lower(): v for k, v in specs.items()}

        brand = (spec_lower.get("brand") or "").strip() or None
        series = spec_lower.get("series") or None
        processor = FlipkartScraping.build_processor(spec_lower)
        ram = spec_lower.get("ram") or None
        storage = spec_lower.get("ssd capacity")
        if not storage:
            storage = next(
                (v for k, v in spec_lower.items() if k.endswith("storage capacity")),
                None,
            )
        screen_size = spec_lower.get("screen size") or None
        graphic_processor = spec_lower.get("graphic processor") or None
        colour = spec_lower.get("color") or None

        images = raw.get("images") or []
        image_url = images[0] if images else None

        return {
            "model_number": model_number,
            "brand": brand,
            "series": series,
            "processor": processor,
            "ram": ram,
            "storage": storage,
            "screen_size": screen_size,
            "graphic_processor": graphic_processor,
            "colour": colour,
            "price": FlipkartScraping.parse_price(raw.get("price")),
            "discount": FlipkartScraping.parse_discount(raw.get("discount")),
            "rating": FlipkartScraping.parse_rating(raw.get("rating")),
            "review_count": FlipkartScraping.parse_review_count(raw.get("reviews")),
            "url": raw.get("url", ""),
            "image_url": image_url,
            "scraped_at": FlipkartDBHelpers.utcnow_naive(),
        }

    @staticmethod
    async def collect_product_urls(
        page, already_scraped: set[str] | None = None
    ) -> list[str]:
        
        print(f" Collecting URLs  (target: {NUMBER_OF_URLS})")

        if already_scraped is None:
            already_scraped = set()

        def page_url(n: int) -> str:
            return CATEGORY_URL if n == 1 else f"{CATEGORY_URL}&page={n}"

        seen_urls: set[str] = set()
        all_urls: list[str] = []
        skipped_count: int = 0
        page_num = 1

        while len(all_urls) < NUMBER_OF_URLS:
            target = page_url(page_num)
            print(f"\n Page {page_num}:")

            try:
                await page.goto(target, wait_until="networkidle", timeout=45000)
            except Exception:
                print(" (networkidle timed out, continuing with what loaded)")

            await page.wait_for_timeout(1500)
            await FlipkartPlaywrightHelpers.handle_captcha(page)
            await FlipkartPlaywrightHelpers.close_login_popup(page)

            if page_num > 1 and f"page={page_num}" not in page.url:
                print(" Redirect detected — waiting 6s then retrying...")
                await asyncio.sleep(6)
                try:
                    await page.goto(target, wait_until="networkidle", timeout=45000)
                except Exception:
                    pass
                await page.wait_for_timeout(2000)
                await FlipkartPlaywrightHelpers.handle_captcha(page)
                if f"page={page_num}" not in page.url:
                    print(" Still wrong page after retry — stopping URL collection.")
                    break

            try:
                await page.locator(".k7wcnx").first.wait_for(
                    state="visible", timeout=12000
                )
            except Exception:
                print(f" No product cards on page {page_num} — stopping")
                break

            cards = await page.locator(".k7wcnx").all()
            new_on_page = 0
            for card in cards:
                href = (await card.get_attribute("href")) or ""
                if href.startswith("/"):
                    clean = BASE_URL + href.split("?")[0]
                    if "/p/" in clean and clean not in seen_urls:
                        seen_urls.add(clean)
                        if clean in already_scraped:
                            skipped_count += 1
                            continue
                        all_urls.append(clean)
                        new_on_page += 1
                        if len(all_urls) >= NUMBER_OF_URLS:
                            break

            print(f" +{new_on_page} new URLs  (total: {len(all_urls)})")

            if len(all_urls) >= NUMBER_OF_URLS:
                print(" Reached target URLS")
                break

            await FlipkartPlaywrightHelpers.simulate_human_scroll(page)
            await FlipkartPlaywrightHelpers.move_mouse_randomly(page)
            wait_sec = random.uniform(2.0, 5.0)
            print(f" Waiting {wait_sec:.1f}s before next page...")
            await asyncio.sleep(wait_sec)
            page_num += 1

        print(
            f"\n Total unique product URLs: {len(all_urls)}  (skipped already-scraped: {skipped_count})"
        )
        return all_urls

    @staticmethod
    async def scrape_product_page(page, url: str) -> dict:
        print(f"Loading URL: {url}")
        await page.goto(url, wait_until="networkidle", timeout=45000)
        await page.wait_for_timeout(2500)
        await FlipkartPlaywrightHelpers.handle_captcha(page)
        await FlipkartPlaywrightHelpers.close_login_popup(page)

        product = {"url": url}
        print(" Extracting product data")

        # price
        for el in await page.locator(FlipkartConstants.PRICE_SEL).all():
            t = (await el.text_content() or "").strip()
            if "₹" in t:
                product["price"] = t
                break

        # discount
        for el in await page.locator(FlipkartConstants.DISCOUNT_SEL).all():
            t = (await el.text_content() or "").strip()
            if re.match(r"^\d+%$", t):
                product["discount"] = t
                break

        # rating
        for el in await page.locator(FlipkartConstants.RATING_SEL).all():
            t = (await el.text_content() or "").strip()
            try:
                float(t)
                product["rating"] = t
                break
            except ValueError:
                pass

        # reviews
        for el in await page.locator(FlipkartConstants.REVIEW_SEL).all():
            t = (await el.text_content() or "").strip()
            if "|" in t:
                product["reviews"] = t.replace("|", "").strip()
                break

        # images
        seen_img, images = set(), []
        for el in await page.locator(FlipkartConstants.IMAGE_SEL).all():
            src = (await el.get_attribute("src")) or ""
            if src and src not in seen_img:
                images.append(src)
                seen_img.add(src)
        product["images"] = images

        # specifications
        spec_tab_selector = FlipkartConstants.SPEC_TAB_SEL
        already_active = False
        try:
            active_text = (
                await page.locator(
                    FlipkartConstants.SPEC_ACTIVE_SEL
                ).first.text_content(timeout=2000)
                or ""
            ).strip()
            if "Specifications" in active_text or "All Details" in active_text:
                already_active = True
        except Exception:
            pass

        if not already_active:
            spec_tab = page.locator(spec_tab_selector).first
            await spec_tab.scroll_into_view_if_needed()
            await spec_tab.click()

        await page.locator(FlipkartConstants.SPEC_GRID_SEL).first.wait_for(
            state="visible", timeout=8000
        )

        try:
            see_more = page.locator(FlipkartConstants.SEE_MORE_SEL).first
            await see_more.scroll_into_view_if_needed()
            await see_more.click(timeout=5000)
            await page.wait_for_function(
                "() => !document.querySelector('[style*=\"max-height: 480px\"]')",
                timeout=5000,
            )
        except Exception:
            pass

        specs = {}
        spec_items = page.locator(FlipkartConstants.SPEC_ITEMS_SEL)
        for i in range(await spec_items.count()):
            item = spec_items.nth(i)
            key = " ".join(
                (
                    await item.locator(
                        FlipkartConstants.SPEC_ITEM_KEY_SEL
                    ).first.text_content()
                    or ""
                ).split()
            )
            val = " ".join(
                (
                    await item.locator(
                        FlipkartConstants.SPEC_ITEM_VALUE_SEL
                    ).first.text_content()
                    or ""
                ).split()
            )
            if key and val:
                specs[key] = val

        product["specifications"] = specs
        return product

    @staticmethod
    def insert_metadata() -> str:
        return str(FlipkartDBHelpers.create_scraping_run())

    @staticmethod
    def fetch_existing_urls() -> list[str]:
        return sorted(list(FlipkartDBHelpers.fetch_scraped_urls()))

    @staticmethod
    def collect_urls(existing_urls: list[str] | None = None) -> list[str]:
        async def _collect() -> list[str]:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=PLAYWRIGHT_HEADLESS,
                    args=[
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--window-size=1440,900",
                    ],
                )
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 900},
                    locale="en-IN",
                    timezone_id="Asia/Kolkata",
                    extra_http_headers={"Accept-Language": "en-IN,en;q=0.9"},
                )
                await context.add_init_script(STEALTH_SCRIPT)
                page = await context.new_page()

                try:
                    return await FlipkartScraping.collect_product_urls(
                        page, set(existing_urls or [])
                    )
                finally:
                    await context.close()
                    await browser.close()

        return asyncio.run(_collect())

    @staticmethod
    def scrape_products(urls: list[str]) -> list[dict]:
        async def _scrape() -> list[dict]:
            if not urls:
                return []

            scraped: list[dict] = []
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=PLAYWRIGHT_HEADLESS,
                    args=[
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--window-size=1440,900",
                    ],
                )
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 900},
                    locale="en-IN",
                    timezone_id="Asia/Kolkata",
                    extra_http_headers={"Accept-Language": "en-IN,en;q=0.9"},
                )
                await context.add_init_script(STEALTH_SCRIPT)
                page = await context.new_page()

                try:
                    for url in urls:
                        try:
                            raw = await FlipkartScraping.scrape_product_page(page, url)
                            scraped.append(raw)
                        except Exception as exc:
                            scraped.append({"url": url, "_error": str(exc)})
                finally:
                    await context.close()
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

            normalised = FlipkartScraping.normalise(raw)
            ok, missing = FlipkartScraping.has_required_fields(normalised)
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
    def update_data(metadata_run_id: str, stats: list[list[dict]]) -> None:
        valid = stats[0] if stats else []
        invalid = stats[1] if stats and len(stats) > 1 else []

        run_uuid = uuid.UUID(metadata_run_id)
        hook = FlipkartDBHelpers.get_hook()
        conn = hook.get_conn()
        cur = conn.cursor()
        try:
            valid_count = 0
            invalid_count = 0

            for row in valid:
                try:
                    product_id = FlipkartDBHelpers.upsert_product(cur, row)
                    FlipkartDBHelpers.upsert_product_details(
                        cur, product_id, run_uuid, row
                    )
                    valid_count += 1
                except Exception as exc:
                    invalid_count += 1
                    FlipkartDBHelpers.log_activity(
                        cur,
                        run_uuid,
                        ActivityTypes.PRODUCT_NOT_FOUND,
                        row.get("url", ""),
                        {"error": str(exc), "product_data": row},
                    )

            for row in invalid:
                invalid_count += 1
                FlipkartDBHelpers.log_activity(
                    cur,
                    run_uuid,
                    row.get("reason", ActivityTypes.FIELD_MISSING),
                    row.get("url", ""),
                    row.get("product_data"),
                )

            conn.commit()
            attempted = valid_count + invalid_count
            FlipkartDBHelpers.finalise_scraping_run(
                run_uuid,
                attempted=attempted,
                valid=valid_count,
                invalid=invalid_count,
            )
        finally:
            cur.close()
            conn.close()
