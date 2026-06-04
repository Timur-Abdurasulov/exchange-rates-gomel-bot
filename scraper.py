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

        # Extract all accent values — order is: USD sell, USD buy, EUR sell, EUR buy, RUB sell, RUB buy
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
