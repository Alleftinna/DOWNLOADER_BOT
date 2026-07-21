from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import InlineQuery, Message, TelegramObject

from downloader_bot.bot.chat_access import is_allowed_inline_query, is_allowed_message


class ChatAccessMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and not is_allowed_message(event):
            return None
        if isinstance(event, InlineQuery) and not is_allowed_inline_query(event):
            return None
        return await handler(event, data)
