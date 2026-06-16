import asyncio
import logging

from aiogram import Bot, Dispatcher

from cookie_generator import CookieGenerator
from downloader_bot.bot.handlers import register_handlers
from downloader_bot.clients.cobalt_client import CobaltClient
from downloader_bot.clients.ytdlp_client import YtdlpClient
from downloader_bot.config import BOT_TOKEN, COOKIE_UPDATE_INTERVAL_HOURS, COOKIES_SAVE_PATH
from downloader_bot.infrastructure.temp_files import clean_data_dir, ensure_data_dir
from downloader_bot.services.download_service import DownloadService
from downloader_bot.services.video_delivery import VideoDeliveryService

logging.basicConfig(level=logging.INFO)


async def main():
    logging.info("Starting bot...")

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is required")

    ensure_data_dir()

    try:
        cookie_generator = CookieGenerator(
            cookies_file=COOKIES_SAVE_PATH,
            update_interval_hours=COOKIE_UPDATE_INTERVAL_HOURS,
        )
        cookie_generator.start()
        logging.info("Cookie generator started successfully")
    except Exception as exc:
        logging.error("Error starting cookie generator: %s", exc)

    clean_data_dir()
    logging.info("Successfully cleaned data directory")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    download_service = DownloadService(CobaltClient(), YtdlpClient())
    delivery_service = VideoDeliveryService(bot)
    register_handlers(dp, bot, download_service, delivery_service)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
