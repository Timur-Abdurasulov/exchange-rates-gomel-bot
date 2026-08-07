import asyncio
import re
from playwright.async_api import async_playwright

TARGET_URL = "https://myfin.by/currency/gomel"

# Add the exact bank names you want to track here (must match the table's first column)
FAVORITE_BANKS = [
    "Искра | БНБ-Банк",
    "BSB-Bank App",
    ]

# Banks to exclude from "best rate" calculation (e.g. exchangers, unreliable apps, etc.)
EXCLUDED_BANKS = [
    "Обменять выгодно",
    "INSNC by Alfa Bank",
    "Up «Суперкурс»",
    "Будь в курсе",
    "MyTechno",
    "Zepter Mobile",
    "Приложение Neo Bank",
    "Myfin Обмен",
    "Банк БелВЭБ",
    "Белинкасгрупп",
    "Беларусбанк\nОнлайн",
    "Забронировать курс",
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

        # ---- Scan the full table once; derive best rates directly from it ----
        table_rows = await _scan_table(page)
        filtered_rows = [
            row for row in table_rows
            if not any(excluded in row["bank"] for excluded in EXCLUDED_BANKS)
        ]
        best = _compute_best_from_table(filtered_rows)

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


def _compute_best_from_table(table_rows: list) -> dict:
    """
    Derive best USD/EUR sell+buy rates directly from the table scan,
    and record which bank(s) hold each best value.
    'Сдать' (sell, you sell to bank) -> highest value is best for you.
    'Купить' (buy, you buy from bank) -> lowest value is best for you.
    """
    best = {
        "USD": {"sell": 0.0, "buy": float("inf"), "sell_banks": [], "buy_banks": []},
        "EUR": {"sell": 0.0, "buy": float("inf"), "sell_banks": [], "buy_banks": []},
    }

    for row in table_rows:
        for currency, sell_key, buy_key in (("USD", "usd_sell", "usd_buy"), ("EUR", "eur_sell", "eur_buy")):
            sell_val = row[sell_key]
            buy_val = row[buy_key]

            if sell_val > best[currency]["sell"]:
                best[currency]["sell"] = sell_val
                best[currency]["sell_banks"] = [row["bank"]]
            elif abs(sell_val - best[currency]["sell"]) < 0.0001:
                if row["bank"] not in best[currency]["sell_banks"]:
                    best[currency]["sell_banks"].append(row["bank"])

            if buy_val < best[currency]["buy"]:
                best[currency]["buy"] = buy_val
                best[currency]["buy_banks"] = [row["bank"]]
            elif abs(buy_val - best[currency]["buy"]) < 0.0001:
                if row["bank"] not in best[currency]["buy_banks"]:
                    best[currency]["buy_banks"].append(row["bank"])

    for currency in ("USD", "EUR"):
        best[currency]["sell"] = round(best[currency]["sell"], 4)
        best[currency]["buy"] = round(best[currency]["buy"], 4)
        print(f"Best {currency} sell: {best[currency]['sell']} at {best[currency]['sell_banks']}")
        print(f"Best {currency} buy: {best[currency]['buy']} at {best[currency]['buy_banks']}")

    return best





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
