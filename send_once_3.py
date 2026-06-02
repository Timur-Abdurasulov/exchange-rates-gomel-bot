import asyncio
from telegram import Bot
from telegram.constants import ParseMode
from scraper import get_best_rates
from datetime import datetime
import os

async def main():
    print("=== Starting ===")
    
    print("Fetching rates...")
    rates = await get_best_rates()
    print(f"Rates received: {rates}")
    
    token = os.environ.get("BOT_TOKEN", "NOT SET")
    channel = os.environ.get("CHANNEL_ID", "NOT SET")
    print(f"BOT_TOKEN set: {'yes' if token != 'NOT SET' else 'NO - MISSING'}")
    print(f"CHANNEL_ID: {channel}")
    
    today = datetime.now().strftime("%d.%m.%Y")
    usd, eur = rates["USD"], rates["EUR"]
    message = (
        f"📅 *{today}*\n\n"
        f"💵 *USD*\n  Купить: `{usd['buy']}` BYN\n  Продать: `{usd['sell']}` BYN\n\n"
        f"💶 *EUR*\n  Купить: `{eur['buy']}` BYN\n  Продать: `{eur['sell']}` BYN\n\n"
        f"Лучшие курсы Гомеля по данным myfin\.by"
    )
    print(f"Message to send:\n{message}")
    
    print("Sending to Telegram...")
    bot = Bot(token=token)
    await bot.send_message(chat_id=channel, text=message, parse_mode=ParseMode.MARKDOWN_V2)
    print("=== Done! Message sent. ===")

asyncio.run(main())
