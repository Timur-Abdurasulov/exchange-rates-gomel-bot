import asyncio
import json
import os
import subprocess
from telegram import Bot, LinkPreviewOptions
from telegram.constants import ParseMode
from scraper import get_best_rates
from datetime import datetime, timezone, timedelta

RATES_FILE = "last_rates.json"

def load_last_rates():
    if os.path.exists(RATES_FILE):
        with open(RATES_FILE, "r") as f:
            return json.load(f)
    return None

def save_rates(data):
    with open(RATES_FILE, "w") as f:
        json.dump(data, f)

def format_delta(old, new):
    if old is None:
        return ""
    delta = round(new - old, 4)
    if delta > 0:
        return f" 🟢 (+{delta})"
    elif delta < 0:
        return f" 🔴 ({delta})"
    return " ➖"

def commit_rates():
    subprocess.run(["git", "config", "user.email", "bot@github.com"], check=True)
    subprocess.run(["git", "config", "user.name", "GitHub Actions Bot"], check=True)
    subprocess.run(["git", "add", RATES_FILE], check=True)
    result = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if result.returncode != 0:
        subprocess.run(["git", "commit", "-m", "Update last rates"], check=True)
        subprocess.run(["git", "push"], check=True)
    else:
        print("No changes to commit")

def format_currency_block(label, rates, last_rates):
    last_sell = last_rates["sell"] if last_rates else None
    last_buy = last_rates["buy"] if last_rates else None

    sell_banks = rates.get("sell_banks", [])
    buy_banks = rates.get("buy_banks", [])
    sell_banks_str = f" — {', '.join(sell_banks)}" if sell_banks else ""
    buy_banks_str = f" — {', '.join(buy_banks)}" if buy_banks else ""

    return (
        f"{label}\n"
        f"  <b>Сдать:</b> <code>{rates['sell']}</code> BYN{format_delta(last_sell, rates['sell'])}{sell_banks_str}\n"
        f"  <b>Купить:</b> <code>{rates['buy']}</code> BYN{format_delta(last_buy, rates['buy'])}{buy_banks_str}\n"
    )

async def main():
    data = await get_best_rates()
    best = data["best"]
    favorites = data["favorites"]

    last_data = load_last_rates()
    last_best = last_data["best"] if last_data else None
    last_favorites = last_data.get("favorites", {}) if last_data else {}

    utc_plus_3 = timezone(timedelta(hours=3))
    today = datetime.now(utc_plus_3).strftime("%d.%m.%Y %H:%M")

    last_usd = last_best["USD"] if last_best else None
    last_eur = last_best["EUR"] if last_best else None

    message = f"📅 <b>{today}</b>\n\n\n"
    message += f"🏆 <b>Лучшие курсы</b>\n\n"
    message += format_currency_block("💵 <b>USD</b>", best["USD"], last_usd) + "\n"
    message += format_currency_block("💶 <b>EUR</b>", best["EUR"], last_eur) + "\n"

    if favorites:
        for bank_name, rates in favorites.items():
            last_bank = last_favorites.get(bank_name)
            last_bank_usd = last_bank["USD"] if last_bank else None
            last_bank_eur = last_bank["EUR"] if last_bank else None

            message += f"\n🏦 <b>{bank_name}</b>\n\n"
            message += format_currency_block("💵 <b>USD</b>", rates["USD"], last_bank_usd) + "\n"
            message += format_currency_block("💶 <b>EUR</b>", rates["EUR"], last_bank_eur)

    message += f"\nhttps://myfin.by/currency/gomel"

    bot = Bot(token=os.environ["BOT_TOKEN"])
    await bot.send_message(chat_id=os.environ["CHANNEL_ID"], text=message, parse_mode=ParseMode.HTML, link_preview_options=LinkPreviewOptions(is_disabled=True))
    print("Sent successfully!")

    save_rates(data)
    commit_rates()

asyncio.run(main())
