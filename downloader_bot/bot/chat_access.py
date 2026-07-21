from aiogram.types import InlineQuery, Message

from downloader_bot.config import ALLOWED_GROUP_ID, RELAY_OWNER_USER_ID


def is_allowed_message(message: Message) -> bool:
    if message.chat.type == "private":
        return bool(message.from_user and message.from_user.id == RELAY_OWNER_USER_ID)
    if message.chat.type in ("group", "supergroup"):
        return bool(ALLOWED_GROUP_ID and message.chat.id == ALLOWED_GROUP_ID)
    return False


def is_allowed_inline_query(query: InlineQuery) -> bool:
    return bool(query.from_user and query.from_user.id == RELAY_OWNER_USER_ID)
