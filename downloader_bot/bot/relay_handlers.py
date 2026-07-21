import logging

from aiogram import Dispatcher, F
from aiogram.types import Message

from downloader_bot.config import RELAY_GROUP_ID
from downloader_bot.services.relay_service import RelayService

logger = logging.getLogger(__name__)


def register_relay_handlers(dp: Dispatcher, relay_service: RelayService) -> None:
    @dp.message(F.chat.id == RELAY_GROUP_ID, F.video | F.document)
    async def on_group_video(message: Message) -> None:
        handled = await relay_service.handle_group_video(message)
        if handled:
            logger.info(
                "Relay matched group video msg_id=%s from=%s",
                message.message_id,
                message.from_user.id if message.from_user else None,
            )
