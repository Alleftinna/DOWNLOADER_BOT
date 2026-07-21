import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import BusinessConnection, Message

from business_bot.connection_store import ConnectionStore

logger = logging.getLogger(__name__)


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

    @dp.message(Command("status"))
    async def cmd_status(message: Message) -> None:
        connected = store.is_connected()
        text = (
            "Business connection: active\n"
            f"Connection ID: {store.get_connection_id()}"
            if connected
            else "Business connection: not connected\n"
            "Connect this bot in Telegram → Settings → Business → Chatbots"
        )
        await bot.send_message(chat_id=message.chat.id, text=text)
