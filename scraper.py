import asyncio
import re
from playwright.async_api import async_playwright

TARGET_URL = "https://myfin.by/currency/gomel"

# Add the exact bank names you want to track here (must match the table's first column)
FAVORITE_BANKS = [
    "Приложение BNB-Bank",
    "Приорбанк",
]


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

        # ---- Best rates from summary box ----
        elements = await page.query_selector_all("span.accent")
        numbers = []
        for el in elements:
            text = await el.inner_text()
            cleaned = re.sub(r'[^\d.,]', '', text.strip())
            try:
                n = float(cleaned.replace(",", "."))
                if 2.0 < n < 5.0:
                    numbers.append(n)
            except ValueError:
                continue

        print(f"Extracted values: {numbers}")

        best = {
            "USD": {"sell": numbers[1], "buy": numbers[0]},
            "EUR": {"sell": numbers[3], "buy": numbers[2]},
        }

        # ---- Favorite bank rates from the full table ----
        favorites = await _extract_favorite_banks(page, FAVORITE_BANKS)

        await browser.close()
        return {"best": best, "favorites": favorites}


async def _extract_favorite_banks(page, bank_names: list) -> dict:
    """
    Scan the table rows and extract USD/EUR sell+buy rates
    for each bank name in bank_names.
    Table columns per row: Bank | USD_sell | USD_buy | EUR_sell | EUR_buy | RUB_sell | RUB_buy | branches
    """
    results = {}
    rows = await page.query_selector_all("table tbody tr")

    for row in rows:
        cells = await row.query_selector_all("td")
        if len(cells) < 5:
            continue

        bank_text = (await cells[0].inner_text()).strip()

        for target_name in bank_names:
            if target_name in bank_text and target_name not in results:
                try:
                    usd_sell = _to_float((await cells[1].inner_text()).strip())
                    usd_buy = _to_float((await cells[2].inner_text()).strip())
                    eur_sell = _to_float((await cells[3].inner_text()).strip())
                    eur_buy = _to_float((await cells[4].inner_text()).strip())
                except IndexError:
                    continue

                if usd_sell and usd_buy and eur_sell and eur_buy:
                    results[target_name] = {
                        "USD": {"sell": usd_sell, "buy": usd_buy},
                        "EUR": {"sell": eur_sell, "buy": eur_buy},
                    }
                    print(f"Found favorite bank '{target_name}': {results[target_name]}")

    for name in bank_names:
        if name not in results:
            print(f"WARNING: favorite bank '{name}' not found in table")

    return results


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", ".").strip())
    except (ValueError, TypeError):
        return None


if __name__ == "__main__":
    async def test():
        rates = await get_best_rates()
        print(rates)
    asyncio.run(test())
