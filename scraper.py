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
        await page.screenshot(path="screenshot.png", full_page=True)

        # Save HTML for debugging
        html = await page.content()
        with open("page.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("HTML saved, length:", len(html))

        await browser.close()
        return {"USD": {"sell": 0, "buy": 0}, "EUR": {"sell": 0, "buy": 0}}

if __name__ == "__main__":
    async def test():
        rates = await get_best_rates()
        print(rates)
    asyncio.run(test())
