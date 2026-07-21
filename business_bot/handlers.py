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


def is_downloader_sender(message: Message) -> bool:
    if not message.from_user:
        return False
    if DOWNLOADER_BOT_USER_ID and message.from_user.id == DOWNLOADER_BOT_USER_ID:
        return True
    if DOWNLOADER_BOT_USERNAME and message.from_user.username:
        return message.from_user.username.lower() == DOWNLOADER_BOT_USERNAME.lower()
    return False


def has_media(message: Message) -> bool:
    return bool(
        message.video or message.document or message.animation or message.video_note,
    )


def should_forward_relay_media(message: Message, store: ConnectionStore, source: str) -> bool:
    if not has_media(message):
        return False
    if is_downloader_sender(message):
        return True
    if source == "business_message" and store.is_relay_pending():
        sender = message.from_user
        logger.info(
            "Accepting business_message media during pending relay from id=%s username=%s",
            sender.id if sender else None,
            sender.username if sender else None,
        )
        return True
    return False


async def forward_video_to_main_bot(
    bot: Bot,
    store: ConnectionStore,
    message: Message,
    source: str,
) -> bool:
    sender_id = message.from_user.id if message.from_user else None

    if not should_forward_relay_media(message, store, source):
        return False

    connection_id = store.get_connection_id()
    if not connection_id:
        logger.error("Cannot forward video: no business connection")
        return False
    if not MAIN_BOT_USER_ID:
        logger.error("Cannot forward video: MAIN_BOT_USER_ID is not configured")
        return False

    logger.info(
        "Forwarding downloader video via %s msg_id=%s chat=%s from=%s",
        source,
        message.message_id,
        message.chat.id,
        sender_id,
    )

    try:
        await bot.copy_message(
            chat_id=MAIN_BOT_USER_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
            business_connection_id=connection_id,
        )
        logger.info(
            "Forwarded video msg_id=%s to main bot user=%s",
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

    @dp.business_message()
    async def on_business_message(message: Message) -> None:
        if not has_media(message):
            return
        sender = message.from_user
        logger.info(
            "business_message media msg_id=%s chat=%s from_id=%s username=%s pending=%s",
            message.message_id,
            message.chat.id,
            sender.id if sender else None,
            sender.username if sender else None,
            store.is_relay_pending(),
        )
        if await forward_video_to_main_bot(bot, store, message, "business_message"):
            logger.info("Handled business_message video from downloader")

    @dp.message(F.video | F.document | F.animation | F.video_note)
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
            f"Downloader bot username: {DOWNLOADER_BOT_USERNAME or '(not set)'}\n"
            f"Main bot user ID: {MAIN_BOT_USER_ID}\n"
            f"Relay pending: {store.is_relay_pending()}"
            if connected
            else "Business connection: not connected\n"
            "Connect this bot in Telegram → Settings → Business → Chatbots"
        )
        await bot.send_message(chat_id=message.chat.id, text=text)
