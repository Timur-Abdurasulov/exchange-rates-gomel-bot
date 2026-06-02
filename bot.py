import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from telegram.constants import ParseMode
from scraper import get_best_rates
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # e.g. "@mychannel" or "-100123456789"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def build_message(rates: dict) -> str:
    today = datetime.now().strftime("%d.%m.%Y")
    usd = rates["USD"]
    eur = rates["EUR"]
    return (
        f"📅 *{today}*\n\n"
        f"💵 *USD*\n"
        f"  Купить: `{usd['buy']}` BYN\n"
        f"  Продать: `{usd['sell']}` BYN\n\n"
        f"💶 *EUR*\n"
        f"  Купить: `{eur['buy']}` BYN\n"
        f"  Продать: `{eur['sell']}` BYN\n\n"
        f"_Лучшие курсы Гомеля по данным myfin.by_"
    )


async def send_rates():
    logger.info("Fetching exchange rates...")
    try:
        rates = await get_best_rates()
        message = build_message(rates)
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        logger.info("Message sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send rates: {e}")


async def main():
    scheduler = AsyncIOScheduler(timezone="UTC")
    # Runs every day at 05:00 UTC
    scheduler.add_job(send_rates, CronTrigger(hour=5, minute=0))
    scheduler.start()
    logger.info("Bot started. Waiting for 05:00 UTC daily trigger...")

    # Optionally send immediately on startup for testing:
    # await send_rates()

    try:
        await asyncio.Event().wait()  # Run forever
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
