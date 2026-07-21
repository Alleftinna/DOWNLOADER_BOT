import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import BusinessConnection, Message

from business_bot.config import DOWNLOADER_BOT_USER_ID, MAIN_BOT_USER_ID
from business_bot.connection_store import ConnectionStore

logger = logging.getLogger(__name__)


async def forward_video_to_main_bot(
    bot: Bot,
    store: ConnectionStore,
    message: Message,
) -> bool:
    if not message.from_user or message.from_user.id != DOWNLOADER_BOT_USER_ID:
        return False
    if not (message.video or message.document):
        return False

    connection_id = store.get_connection_id()
    if not connection_id:
        logger.error("Cannot forward video: no business connection")
        return False
    if not MAIN_BOT_USER_ID:
        logger.error("Cannot forward video: MAIN_BOT_USER_ID is not configured")
        return False

    try:
        await bot.copy_message(
            chat_id=MAIN_BOT_USER_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
            business_connection_id=connection_id,
        )
        logger.info(
            "Forwarded video msg_id=%s from downloader to main bot user=%s",
            message.message_id,
            MAIN_BOT_USER_ID,
        )
        return True
    except Exception as exc:
        logger.exception("Failed to forward video to main bot: %s", exc)
        return False


def register_handlers(dp: Dispatcher, bot: Bot, store: ConnectionStore) -> None:
    @dp.business_connection()
    async def on_business_connection(connection: BusinessConnection) -> None:
        if connection.is_enabled:
            store.save(connection.id, connection.user.id)
            logger.info(
                "Business connection enabled: id=%s user=%s",
                connection.id,
                connection.user.id,
            )
        else:
            store.clear()
            logger.info("Business connection disabled: id=%s", connection.id)

    @dp.business_message(F.video | F.document)
    async def on_business_downloader_video(message: Message) -> None:
        if await forward_video_to_main_bot(bot, store, message):
            logger.info("Handled business_message video from downloader")

    @dp.message(F.video | F.document)
    async def on_downloader_video(message: Message) -> None:
        if await forward_video_to_main_bot(bot, store, message):
            logger.info("Handled message video from downloader")

    @dp.message(Command("status"))
    async def cmd_status(message: Message) -> None:
        connected = store.is_connected()
        text = (
            "Business connection: active\n"
            f"Connection ID: {store.get_connection_id()}\n"
            f"Downloader bot user ID: {DOWNLOADER_BOT_USER_ID}\n"
            f"Main bot user ID: {MAIN_BOT_USER_ID}"
            if connected
            else "Business connection: not connected\n"
            "Connect this bot in Telegram → Settings → Business → Chatbots"
        )
        await bot.send_message(chat_id=message.chat.id, text=text)
