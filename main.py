import asyncio
import logging

from aiogram import Bot, Dispatcher

from downloader_bot.bot.handlers import register_handlers
from downloader_bot.bot.relay_handlers import register_relay_handlers
from downloader_bot.clients.business_relay_client import BusinessRelayClient
from downloader_bot.clients.cobalt_client import CobaltClient
from downloader_bot.clients.ytdlp_client import YtdlpClient
from downloader_bot.config import (
    BOT_TOKEN,
    BUSINESS_BOT_URL,
    COBALT_API_URL,
    DOWNLOADER_URL,
    RELAY_BOT_USER_ID,
    RELAY_GROUP_ID,
    RELAY_OWNER_USER_ID,
    RELAY_TIMEOUT_SECONDS,
)
from downloader_bot.infrastructure.cobalt_health import check_cobalt_reachable
from downloader_bot.infrastructure.temp_files import clean_data_dir, ensure_data_dir
from downloader_bot.services.download_service import DownloadService
from downloader_bot.services.relay_service import RelayService
from downloader_bot.services.video_delivery import VideoDeliveryService

logging.basicConfig(level=logging.INFO)


async def main():
    logging.info("Starting bot...")

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is required")

    ensure_data_dir()
    clean_data_dir()
    logging.info("Successfully cleaned data directory")

    logging.info("COBALT_API_URL=%s", COBALT_API_URL)
    logging.info("DOWNLOADER_URL=%s", DOWNLOADER_URL)
    logging.info(
        "Relay: group_id=%s timeout=%ss bot_user_id=%s owner_id=%s business_bot=%s",
        RELAY_GROUP_ID,
        RELAY_TIMEOUT_SECONDS,
        RELAY_BOT_USER_ID,
        RELAY_OWNER_USER_ID,
        BUSINESS_BOT_URL,
    )

    business_client = BusinessRelayClient()
    business_ok, business_message = await business_client.check_health()
    if business_ok:
        logging.info("Business bot reachable: %s", business_message)
    else:
        logging.warning(
            "Business bot unreachable at %s — %s. Relay will fallback to Cobalt/yt-dlp.",
            BUSINESS_BOT_URL,
            business_message,
        )

    cobalt_ok, cobalt_message = await check_cobalt_reachable()
    if cobalt_ok:
        logging.info("Cobalt reachable: %s", cobalt_message)
    else:
        logging.warning(
            "Cobalt unreachable at %s — %s. Downloads will use yt-dlp fallback only until this is fixed.",
            COBALT_API_URL,
            cobalt_message,
        )

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    download_service = DownloadService(CobaltClient(), YtdlpClient())
    delivery_service = VideoDeliveryService(bot)
    relay_service = RelayService(bot, download_service, delivery_service, business_client)
    register_handlers(dp, bot, download_service, delivery_service, relay_service)
    register_relay_handlers(dp, relay_service)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
