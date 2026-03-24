import asyncio
import random


class FlipkartPlaywrightHelpers:
    @staticmethod
    async def close_login_popup(page):
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(600)
        for sel in ['button[aria-label="Close"]', ':text("✕")', ':text("×")']:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=800):
                    await btn.click(timeout=1500)
                    await page.wait_for_timeout(400)
                    return
            except Exception:
                continue

    @staticmethod
    async def handle_captcha(page, max_wait_seconds=120):
        signals = [
            'text="Are you a human"',
            'text="verify you are human"',
            'text="Enter the characters"',
            'iframe[src*="recaptcha"]',
            'iframe[src*="captcha"]',
        ]
        for sig in signals:
            try:
                el = page.locator(sig).first
                if await el.is_visible(timeout=1000):
                    print("\n  ⚠  CAPTCHA detected! Solve it in the browser window.")
                    print(f"     Waiting up to {max_wait_seconds}s...")
                    await el.wait_for(state="hidden", timeout=max_wait_seconds * 1000)
                    print("     ✓ CAPTCHA resolved, continuing...")
                    await page.wait_for_timeout(1000)
                    return True
            except Exception:
                continue
        return False

    @staticmethod
    async def human_like_delay(min_ms=1200, max_ms=3000):
        await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))

    @staticmethod
    async def simulate_human_scroll(page):
        total_height = await page.evaluate("() => document.body.scrollHeight")
        current = 0
        while current < total_height * 0.6:
            step = random.randint(200, 500)
            current = min(current + step, total_height)
            await page.evaluate(
                f"window.scrollTo({{top: {current}, behavior: 'smooth'}})"
            )
            await asyncio.sleep(random.uniform(0.1, 0.3))

    @staticmethod
    async def move_mouse_randomly(page):
        for _ in range(random.randint(2, 4)):
            x = random.randint(100, 1100)
            y = random.randint(100, 700)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.05, 0.15))
