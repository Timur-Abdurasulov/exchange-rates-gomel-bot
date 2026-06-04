import asyncio
from playwright.async_api import async_playwright

TARGET_URL = "https://myfin.by/currency/gomel"

async def get_best_rates() -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()
        await page.goto(TARGET_URL, wait_until="networkidle", timeout=60_000)

        # Dismiss cookie popup if present
        try:
            accept_btn = await page.wait_for_selector("button.btn-cookie-accept, button.js-cookie-accept, a.btn--green", timeout=5000)
            if accept_btn:
                await accept_btn.click()
                await page.wait_for_timeout(1000)
        except Exception:
            pass  # No popup, continue

        # Wait for the summary rates to appear
        await page.wait_for_selector("span.accent", timeout=10000)

        # Scope to the best rates summary block
        summary = await page.query_selector("div.course-brief-info--best-courses")
        if summary:
            values = await summary.query_selector_all("span.accent")
        else:
            # Fallback to all accent spans
            values = await page.query_selector_all("span.accent")

        numbers = []
        for v in values:
            text = await v.inner_text()
            try:
                numbers.append(float(text.strip().replace(",", ".")))
            except ValueError:
                continue

        print(f"Extracted accent values: {numbers}")
        await browser.close()

        return {
            "USD": {"sell": numbers[0], "buy": numbers[1]},
            "EUR": {"sell": numbers[2], "buy": numbers[3]},
        }

if __name__ == "__main__":
    async def test():
        rates = await get_best_rates()
        print(rates)
    asyncio.run(test())
