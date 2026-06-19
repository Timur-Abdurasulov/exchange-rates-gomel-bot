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
    # Only commit if there are actual changes
    result = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if result.returncode != 0:
        subprocess.run(["git", "commit", "-m", "Update last rates"], check=True)
        subprocess.run(["git", "push"], check=True)
    else:
        print("No changes to commit")

async def main():
    data = await get_best_rates()
    best = data["best"]
    favorites = data["favorites"]

    last_data = load_last_rates()
    last_best = last_data["best"] if last_data else None

    utc_plus_3 = timezone(timedelta(hours=3))
    today = datetime.now(utc_plus_3).strftime("%d.%m.%Y %H:%M")

    usd, eur = best["USD"], best["EUR"]
    last_usd = last_best["USD"] if last_best else None
    last_eur = last_best["EUR"] if last_best else None

    message = (
        f"📅 <b>{today}</b>\n\n"
        f"🏆 <b>Лучшие курсы</b>\n\n"
        f"💵 <b>USD</b>\n"
        f"  Сдать: <code>{usd['sell']}</code> BYN{format_delta(last_usd['sell'] if last_usd else None, usd['sell'])}\n"
        f"  Купить: <code>{usd['buy']}</code> BYN{format_delta(last_usd['buy'] if last_usd else None, usd['buy'])}\n\n"
        f"💶 <b>EUR</b>\n"
        f"  Сдать: <code>{eur['sell']}</code> BYN{format_delta(last_eur['sell'] if last_eur else None, eur['sell'])}\n"
        f"  Купить: <code>{eur['buy']}</code> BYN{format_delta(last_eur['buy'] if last_eur else None, eur['buy'])}\n"
    )

    if favorites:
        for bank_name, rates in favorites.items():
            f_usd, f_eur = rates["USD"], rates["EUR"]
            message += f"\n🏦 <b>{bank_name}</b>\n"
            message += f"💵 USD — Сдать: <code>{f_usd['sell']}</code> / Купить: <code>{f_usd['buy']}</code>\n"
            message += f"💶 EUR — Сдать: <code>{f_eur['sell']}</code> / Купить: <code>{f_eur['buy']}</code>\n"

    message += f"\nhttps://myfin.by/currency/gomel"

    bot = Bot(token=os.environ["BOT_TOKEN"])
    await bot.send_message(chat_id=os.environ["CHANNEL_ID"], text=message, parse_mode=ParseMode.HTML, link_preview_options=LinkPreviewOptions(is_disabled=True))
    print("Sent successfully!")

    save_rates(data)
    commit_rates()

asyncio.run(main())
