"""
Scraper for myfin.by/currency/gomel
Uses Playwright (headless Chromium) because the page is rendered by JavaScript.

Returns the BEST rates across all listed banks:
  - best buy  = highest "buy" rate  (bank pays you the most for your currency)
  - best sell = lowest  "sell" rate (bank charges you the least when you buy currency)
"""

import asyncio
import re
from playwright.async_api import async_playwright


TARGET_URL = "https://myfin.by/currency/gomel"

# Selectors — adjust if the site changes its markup
# The main table rows for USD and EUR appear under the "В банках" (in-banks) tab
TABLE_ROW_SELECTOR = "table tbody tr"


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
        usd = await _scrape_currency_page(context, "https://myfin.by/currency/usd/gomel", min_rate=2.5, max_rate=4.0)
        eur = await _scrape_currency_page(context, "https://myfin.by/currency/eur/gomel", min_rate=3.0, max_rate=5.0)
        await browser.close()
        return {"USD": usd, "EUR": eur}


async def _scrape_currency_page(context, url: str, min_rate: float, max_rate: float) -> dict:
    page = await context.new_page()
    await page.goto(url, wait_until="networkidle", timeout=60_000)
    result = await _extract_rates_from_dom(page, min_rate, max_rate)
    await page.close()
    return result

    async def handle_response(response):
        if response.status == 200 and "json" in response.headers.get("content-type", ""):
            try:
                body = await response.json()
                json_rows.append(body)
            except Exception:
                pass

    page.on("response", handle_response)
    await page.goto(url, wait_until="networkidle", timeout=60_000)

    # Try JSON intercept first
    result = _extract_rates_from_json(json_rows)
    if result:
        await page.close()
        return result

    # Fallback: DOM
    result = await _extract_rates_from_dom(page)
    await page.close()
    return result


def _parse_from_json(rates_data: dict) -> dict | None:
    """Try to find USD/EUR rates in any captured JSON response."""
    best = {
        "USD": {"buy": 0.0, "sell": float("inf")},
        "EUR": {"buy": 0.0, "sell": float("inf")},
    }
    found_any = False

    for url, data in rates_data.items():
        # The structure varies; try common patterns
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Try known keys
            for key in ("data", "rates", "result", "items", "currencies"):
                if isinstance(data.get(key), list):
                    items = data[key]
                    break

        for item in items:
            if not isinstance(item, dict):
                continue
            currency = str(item.get("currency", item.get("iso", item.get("code", "")))).upper()
            if currency not in ("USD", "EUR"):
                continue
            buy = _to_float(item.get("buy", item.get("buyRate", item.get("rateBuy"))))
            sell = _to_float(item.get("sell", item.get("sellRate", item.get("rateSell"))))
            if buy and sell:
                found_any = True
                if buy > best[currency]["buy"]:
                    best[currency]["buy"] = buy
                if sell < best[currency]["sell"]:
                    best[currency]["sell"] = sell

    if found_any and best["USD"]["buy"] > 0 and best["EUR"]["buy"] > 0:
        return {
            "USD": {
                "buy": round(best["USD"]["buy"], 4),
                "sell": round(best["USD"]["sell"], 4),
            },
            "EUR": {
                "buy": round(best["EUR"]["buy"], 4),
                "sell": round(best["EUR"]["sell"], 4),
            },
        }
    return None


async def _parse_from_dom(page) -> dict:
    """
    Fallback: read the rendered rate table from the DOM.
    Columns: Bank | Currency | Buy | Sell | Updated
    """
    best = {
        "USD": {"buy": 0.0, "sell": float("inf")},
        "EUR": {"buy": 0.0, "sell": float("inf")},
    }

    rows = await page.query_selector_all(TABLE_ROW_SELECTOR)
    for row in rows:
        cells = await row.query_selector_all("td")
        if len(cells) < 4:
            continue
        texts = [await c.inner_text() for c in cells]

        # Detect which column holds currency name/code
        currency = None
        buy = sell = None

        # Try to find "USD" or "EUR" in any cell
        for i, t in enumerate(texts):
            if "USD" in t.upper() or "доллар" in t.lower():
                currency = "USD"
            elif "EUR" in t.upper() or "евро" in t.lower():
                currency = "EUR"

        if currency is None:
            continue

        # Find two numeric values (buy and sell)
        numbers = []
        for t in texts:
            n = _to_float(t.strip())
            if n and 1 < n < 100:  # sanity range for BYN rates
                numbers.append(n)

        if len(numbers) >= 2:
            buy_val, sell_val = numbers[0], numbers[1]
            if buy_val > best[currency]["buy"]:
                best[currency]["buy"] = buy_val
            if sell_val < best[currency]["sell"]:
                best[currency]["sell"] = sell_val

    # Last resort: pull the "best rate" summary shown at the top of the page
    if best["USD"]["buy"] == 0:
        best = await _parse_best_summary(page)

    return {
        "USD": {
            "buy": round(best["USD"]["buy"], 4),
            "sell": round(best["USD"]["sell"], 4),
        },
        "EUR": {
            "buy": round(best["EUR"]["buy"], 4),
            "sell": round(best["EUR"]["sell"], 4),
        },
    }


async def _parse_best_summary(page) -> dict:
    """
    myfin.by shows a prominent 'best rates' box near the top.
    Grab the text of the whole page and regex-extract numbers near USD/EUR labels.
    """
    best = {
        "USD": {"buy": 0.0, "sell": float("inf")},
        "EUR": {"buy": 0.0, "sell": float("inf")},
    }

    content = await page.content()
    # Look for patterns like: USD ... 2.84 ... 2.85
    for currency in ("USD", "EUR"):
        # Find all decimal numbers after the currency symbol
        pattern = re.compile(
            rf"{currency}.*?(\d+[.,]\d{{2,4}}).*?(\d+[.,]\d{{2,4}})",
            re.DOTALL,
        )
        match = pattern.search(content)
        if match:
            n1 = _to_float(match.group(1))
            n2 = _to_float(match.group(2))
            if n1 and n2:
                best[currency]["sell"] = min(n1, n2)
                best[currency]["buy"] = max(n1, n2)

    return best


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", ".").strip())
    except (ValueError, TypeError):
        return None


def _extract_rates_from_json(json_list: list) -> dict | None:
    best_buy = 0.0
    best_sell = float("inf")

    for data in json_list:
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            for key in ("data", "rates", "result", "items", "currencies"):
                if isinstance(data.get(key), list):
                    items = data[key]
                    break

        for item in items:
            if not isinstance(item, dict):
                continue
            print(f"JSON item keys: {list(item.keys())}, values: {item}")
            buy = _to_float(item.get("buy", item.get("buyRate", item.get("rateBuy"))))
            sell = _to_float(item.get("sell", item.get("sellRate", item.get("rateSell"))))
            if buy and sell and buy > 0 and sell > 0:
              if buy > best_buy:   # highest buy rate
                best_buy = buy
              if sell < best_sell: # lowest sell rate
                best_sell = sell

    if best_buy > 0 and best_sell < float("inf"):
        return {"buy": round(best_buy, 4), "sell": round(best_sell, 4)}
    return None


async def _extract_rates_from_dom(page, min_rate: float, max_rate: float) -> dict:
    best_buy = float("inf")   # lowest bank sell price = cheapest for you to buy
    best_sell = 0.0           # highest bank buy price = most you get when selling

    rows = await page.query_selector_all("table tbody tr")
    for row in rows:
        cells = await row.query_selector_all("td")
        if len(cells) < 3:
            continue
        # Only look at cells 1 and 2 (sell and buy columns), skip cell 0 (bank name)
        try:
            sell_val = _to_float((await cells[1].inner_text()).strip())
            buy_val = _to_float((await cells[2].inner_text()).strip())
        except IndexError:
            continue

        if not sell_val or not buy_val:
            continue
        # Strict range filter — only accept values in the expected rate range
        if not (min_rate < sell_val < max_rate and min_rate < buy_val < max_rate):
            continue

        if sell_val > best_sell:
            best_sell = sell_val
        if buy_val < best_buy:
            best_buy = buy_val

    return {
        "sell": round(best_sell, 4),
        "buy": round(best_buy, 4),
    }


# Quick test
if __name__ == "__main__":
    async def test():
        rates = await get_best_rates()
        print(rates)
    asyncio.run(test())
