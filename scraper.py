import asyncio
import re
from playwright.async_api import async_playwright

TARGET_URL = "https://myfin.by/currency/gomel"

# Add the exact bank names you want to track here (must match the table's first column)
FAVORITE_BANKS = [
    "Приложение BNB-Bank",
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

        # ---- Best rates from summary box (numbers only) ----
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

        # ---- Scan the full table to find which bank(s) match each best rate ----
        table_rows = await _scan_table(page)
        best_banks = _find_best_rate_banks(best, table_rows)
        best["USD"]["sell_banks"] = best_banks["USD"]["sell"]
        best["USD"]["buy_banks"] = best_banks["USD"]["buy"]
        best["EUR"]["sell_banks"] = best_banks["EUR"]["sell"]
        best["EUR"]["buy_banks"] = best_banks["EUR"]["buy"]

        # ---- Favorite bank rates from the full table ----
        favorites = _extract_favorite_banks(table_rows, FAVORITE_BANKS)

        await browser.close()
        return {"best": best, "favorites": favorites}


async def _scan_table(page) -> list:
    """
    Reads the full rate table once and returns a list of dicts:
    [{"bank": str, "usd_sell": float, "usd_buy": float, "eur_sell": float, "eur_buy": float}, ...]
    """
    rows_data = []
    rows = await page.query_selector_all("table tbody tr")

    for row in rows:
        cells = await row.query_selector_all("td")
        if len(cells) < 5:
            continue

        bank_text = (await cells[0].inner_text()).strip()
        # Skip rows that look like branch/address sub-rows (they start with city names, not bank names)
        if not bank_text or bank_text.startswith(("г.", " г.", "Гомель,")):
            continue

        try:
            usd_sell = _to_float((await cells[1].inner_text()).strip())
            usd_buy = _to_float((await cells[2].inner_text()).strip())
            eur_sell = _to_float((await cells[3].inner_text()).strip())
            eur_buy = _to_float((await cells[4].inner_text()).strip())
        except IndexError:
            continue

        if usd_sell and usd_buy and eur_sell and eur_buy:
            rows_data.append({
                "bank": bank_text,
                "usd_sell": usd_sell,
                "usd_buy": usd_buy,
                "eur_sell": eur_sell,
                "eur_buy": eur_buy,
            })

    return rows_data


def _find_best_rate_banks(best: dict, table_rows: list) -> dict:
    """
    For each of the 4 best values, find which bank(s) in the table match it exactly.
    Returns lists of bank names (could be more than one bank tied for best).
    """
    result = {
        "USD": {"sell": [], "buy": []},
        "EUR": {"sell": [], "buy": []},
    }

    targets = {
        ("USD", "sell"): best["USD"]["sell"],
        ("USD", "buy"): best["USD"]["buy"],
        ("EUR", "sell"): best["EUR"]["sell"],
        ("EUR", "buy"): best["EUR"]["buy"],
    }

    field_map = {
        ("USD", "sell"): "usd_sell",
        ("USD", "buy"): "usd_buy",
        ("EUR", "sell"): "eur_sell",
        ("EUR", "buy"): "eur_buy",
    }

    for key, target_value in targets.items():
        field = field_map[key]
        matches = [
            row["bank"] for row in table_rows
            if abs(row[field] - target_value) < 0.0001
        ]
        currency, side = key
        result[currency][side] = matches
        print(f"Best {currency} {side} ({target_value}) found at: {matches}")

    return result


def _extract_favorite_banks(table_rows: list, bank_names: list) -> dict:
    """Find rates for specific favorite banks from the already-scanned table."""
    results = {}

    for row in table_rows:
        for target_name in bank_names:
            if target_name in row["bank"] and target_name not in results:
                results[target_name] = {
                    "USD": {"sell": row["usd_sell"], "buy": row["usd_buy"]},
                    "EUR": {"sell": row["eur_sell"], "buy": row["eur_buy"]},
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
