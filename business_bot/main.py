import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher

from business_bot.config import BUSINESS_API_PORT, BUSINESS_BOT_TOKEN, BUSINESS_CONNECTION_FILE
from business_bot.connection_store import ConnectionStore
from business_bot.handlers import register_handlers
from business_bot.relay_api import create_relay_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    if not BUSINESS_BOT_TOKEN:
        raise RuntimeError("BUSINESS_BOT_TOKEN is required")

    store = ConnectionStore(BUSINESS_CONNECTION_FILE)
    bot = Bot(token=BUSINESS_BOT_TOKEN)
    dp = Dispatcher()
    register_handlers(dp, bot, store)

    relay_app = create_relay_app(bot, store)
    runner = web.AppRunner(relay_app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=BUSINESS_API_PORT)
    await site.start()
    logger.info(
        "Business relay API listening on 0.0.0.0:%s (connected=%s)",
        BUSINESS_API_PORT,
        store.is_connected(),
    )

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
