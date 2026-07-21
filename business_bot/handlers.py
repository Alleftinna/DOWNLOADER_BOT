import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import BusinessConnection, Message

from business_bot.config import (
    DOWNLOADER_BOT_USER_ID,
    DOWNLOADER_BOT_USERNAME,
    MAIN_BOT_USER_ID,
)
from business_bot.connection_store import ConnectionStore

logger = logging.getLogger(__name__)

_MEDIA_FILTER = F.video | F.document | F.animation


def is_downloader_sender(message: Message) -> bool:
    if not message.from_user:
        return False
    if DOWNLOADER_BOT_USER_ID and message.from_user.id == DOWNLOADER_BOT_USER_ID:
        return True
    if DOWNLOADER_BOT_USERNAME and message.from_user.username:
        return message.from_user.username.lower() == DOWNLOADER_BOT_USERNAME.lower()
    return False


async def forward_video_to_main_bot(
    bot: Bot,
    store: ConnectionStore,
    message: Message,
    source: str,
) -> bool:
    sender_id = message.from_user.id if message.from_user else None
    sender_username = message.from_user.username if message.from_user else None

    if not is_downloader_sender(message):
        logger.debug(
            "Skip %s video from_id=%s username=%s (expected downloader %s)",
            source,
            sender_id,
            sender_username,
            DOWNLOADER_BOT_USER_ID,
        )
        return False

    connection_id = store.get_connection_id()
    if not connection_id:
        logger.error("Cannot forward video: no business connection")
        return False
    if not MAIN_BOT_USER_ID:
        logger.error("Cannot forward video: MAIN_BOT_USER_ID is not configured")
        return False

    logger.info(
        "Downloader video received via %s msg_id=%s chat=%s",
        source,
        message.message_id,
        message.chat.id,
    )

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

    @dp.business_message(_MEDIA_FILTER)
    async def on_business_downloader_video(message: Message) -> None:
        if await forward_video_to_main_bot(bot, store, message, "business_message"):
            logger.info("Handled business_message video from downloader")

    @dp.message(_MEDIA_FILTER)
    async def on_downloader_video(message: Message) -> None:
        if await forward_video_to_main_bot(bot, store, message, "message"):
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
