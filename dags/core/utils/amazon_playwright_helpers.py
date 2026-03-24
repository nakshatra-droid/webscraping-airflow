import asyncio
import random

from playwright.async_api import async_playwright, TimeoutError as PWTimeout
from playwright_stealth import Stealth

from core.constants.constants_values import AmazonConstants


USER_AGENT = AmazonConstants.USER_AGENT


class AmazonPlaywrightHelpers:
    @staticmethod
    async def make_context(playwright):
        """
        Launch browser and apply playwright-stealth to the context.

        playwright-stealth patches ~15 fingerprint signals that manual scripts miss:
          - navigator.webdriver / plugins / languages / platform / vendor
          - WebGL vendor + renderer  (headless default = "Google SwiftShader" — dead giveaway)
          - chrome.app / chrome.csi / chrome.loadTimes
          - media codec fingerprint
          - iframe.contentWindow proxy leak
          - hairline pixel detection
          - Sec-CH-UA headers
          - Error.prototype stack trace proxy leak

        We apply it to the CONTEXT (not per-page) so every new page
        automatically gets all patches via add_init_script.
        """
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--window-size=1440,900",
            ],
        )
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=USER_AGENT,
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            extra_http_headers={
                "Accept-Language": "en-IN,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
            },
        )

        # Apply full playwright-stealth to context
        stealth = Stealth(
            navigator_languages_override=("en-IN", "en"),
            navigator_platform_override="Win32",
            webgl_vendor_override="Intel Inc.",
            webgl_renderer_override="Intel Iris OpenGL Engine",
        )
        await stealth.apply_stealth_async(ctx)

        return browser, ctx

    @staticmethod
    async def human_scroll(page):
        """Scroll down the page in random increments like a real user."""
        try:
            total_h = (
                await page.evaluate("document.body ? document.body.scrollHeight : 4000")
                or 4000
            )
        except Exception:
            total_h = 4000

        steps = random.randint(6, 10)
        for i in range(1, steps + 1):
            y = int((total_h / steps) * i)
            await page.mouse.wheel(0, random.randint(150, 350))
            try:
                await page.evaluate(f"window.scrollTo({{top:{y}, behavior:'smooth'}})")
            except Exception:
                pass
            await asyncio.sleep(random.uniform(0.3, 0.7))

        try:
            await page.evaluate("window.scrollTo({top:300, behavior:'smooth'})")
        except Exception:
            pass
        await asyncio.sleep(0.5)

    @staticmethod
    async def move_mouse_randomly(page):
        """Move mouse to random positions — bot detectors watch for mouse inactivity."""
        for _ in range(random.randint(2, 4)):
            x = random.randint(100, 1200)
            y = random.randint(100, 700)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.05, 0.15))

    @staticmethod
    async def handle_captcha(page, max_wait_seconds=120) -> bool:
        """
        Detect CAPTCHA / robot-check signals.
        If found, pauses up to max_wait_seconds for manual solve.
        Returns True if a CAPTCHA was found (and presumably solved), False otherwise.
        """
        signals = [
            'text="Enter the characters you see below"',
            'text="Sorry, we just need to make sure"',
            'text="Type the characters you see in this image"',
            'iframe[src*="captcha"]',
            '[action*="/errors/validateCaptcha"]',
        ]
        for sig in signals:
            try:
                el = page.locator(sig).first
                if await el.is_visible(timeout=1000):
                    print("\n  ⚠  CAPTCHA detected!")
                    print("     Solve it in the browser window.")
                    print(f"     Waiting up to {max_wait_seconds}s...")
                    await el.wait_for(state="hidden", timeout=max_wait_seconds * 1000)
                    print("     ✓ CAPTCHA resolved, continuing...")
                    await asyncio.sleep(1)
                    return True
            except Exception:
                continue
        return False

    @staticmethod
    async def close_any_popups(page):
        """Dismiss location/signin/notification popups that might cover content."""
        for sel in [
            'input[data-action-type="DISMISS"]',
            '[data-testid="hmenu-close-btn"]',
            'button[data-action="a-popover-close"]',
            ".a-popover-closebutton",
        ]:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=600):
                    await btn.click(timeout=1000)
                    await asyncio.sleep(0.3)
                    return
            except Exception:
                continue
