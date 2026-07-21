import logging

from aiogram import Dispatcher, F
from aiogram.types import Message

from downloader_bot.config import RELAY_OWNER_USER_ID
from downloader_bot.services.relay_service import RelayService

logger = logging.getLogger(__name__)


def register_relay_handlers(dp: Dispatcher, relay_service: RelayService) -> None:
    if not RELAY_OWNER_USER_ID:
        logger.warning("RELAY_OWNER_USER_ID is not set — owner video relay handler disabled")
        return

    @dp.message(
        F.chat.type == "private",
        F.from_user.id == RELAY_OWNER_USER_ID,
        F.video | F.document,
    )
    async def on_owner_relay_video(message: Message) -> None:
        handled = await relay_service.handle_owner_video(message)
        if handled:
            logger.info(
                "Relay matched owner video msg_id=%s from=%s",
                message.message_id,
                message.from_user.id if message.from_user else None,
            )
