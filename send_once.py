import asyncio
from telegram import Bot
from telegram.constants import ParseMode
from scraper import get_best_rates
from datetime import datetime, timezone, timedelta
import os

async def main():
    rates = await get_best_rates()
    utc_plus_3 = timezone(timedelta(hours=3))
    today = datetime.now(utc_plus_3).strftime("%d.%m.%Y %H:%M")
    usd, eur = rates["USD"], rates["EUR"]
    message = (
        f"📅 <b>{today}</b>\n\n"
        f"💵 <b>USD</b>\n"
        f"  Сдать: <code>{usd['buy']}</code> BYN\n"
        f"  Купить: <code>{usd['sell']}</code> BYN\n\n"
        f"💶 <b>EUR</b>\n"
        f"  Сдать: <code>{eur['buy']}</code> BYN\n"
        f"  Купить: <code>{eur['sell']}</code> BYN\n\n"
    
    )
    rates = await get_best_rates()
    print(f"Raw rates: {rates}")
    
    bot = Bot(token=os.environ["BOT_TOKEN"])
    await bot.send_message(chat_id=os.environ["CHANNEL_ID"], text=message, parse_mode=ParseMode.HTML)
    print("Sent successfully!")

asyncio.run(main())
