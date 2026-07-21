import logging

from aiohttp import web
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from business_bot.config import DOWNLOADER_BOT_USER_ID, get_downloader_chat_id
from business_bot.connection_store import ConnectionStore

logger = logging.getLogger(__name__)

_PEER_ID_INVALID_HINT = (
    "PEER_ID_INVALID: Telegram has no private chat between your account and the "
    "downloader bot. From the owner account (RELAY_OWNER_USER_ID): open the "
    "downloader bot and send /start, then verify DOWNLOADER_BOT_USER_ID or set "
    "DOWNLOADER_BOT_USERNAME. If both bots are yours, enable bot-to-bot in BotFather."
)


def create_relay_app(bot: Bot, store: ConnectionStore) -> web.Application:
    app = web.Application()

    async def health(_request: web.Request) -> web.Response:
        connected = store.is_connected()
        return web.json_response(
            {
                "ok": True,
                "business_connection": connected,
                "downloader_bot_chat_id": get_downloader_chat_id() or None,
                "downloader_bot_user_id": DOWNLOADER_BOT_USER_ID or None,
            }
        )

    async def relay(request: web.Request) -> web.Response:
        connection_id = store.get_connection_id()
        if not connection_id:
            return web.json_response(
                {"error": "no business connection — connect bot in Telegram Business settings"},
                status=503,
            )

        downloader_chat_id = get_downloader_chat_id()
        if not downloader_chat_id:
            return web.json_response(
                {"error": "DOWNLOADER_BOT_USER_ID or DOWNLOADER_BOT_USERNAME is not configured"},
                status=503,
            )

        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "invalid json"}, status=400)

        url = (body.get("url") or "").strip()
        if not url:
            return web.json_response({"error": "url is required"}, status=400)

        try:
            # Bot-to-bot direct chat: downloader replies to business bot (we receive it).
            # Business-connection send goes as owner: downloader replies to owner chat
            # and business bot never gets the video update.
            try:
                sent = await bot.send_message(chat_id=downloader_chat_id, text=url)
                logger.info(
                    "Relay sent url=%s via bot-to-bot chat=%s msg_id=%s",
                    url,
                    downloader_chat_id,
                    sent.message_id,
                )
            except TelegramBadRequest as direct_exc:
                logger.warning(
                    "Direct bot-to-bot send failed (%s), trying business connection",
                    direct_exc,
                )
                sent = await bot.send_message(
                    chat_id=downloader_chat_id,
                    text=url,
                    business_connection_id=connection_id,
                )
                logger.info(
                    "Relay sent url=%s via business connection chat=%s msg_id=%s",
                    url,
                    downloader_chat_id,
                    sent.message_id,
                )
            return web.json_response({"ok": True, "message_id": sent.message_id})
        except TelegramBadRequest as exc:
            if "PEER_ID_INVALID" in str(exc):
                logger.error("%s chat_id=%s", _PEER_ID_INVALID_HINT, downloader_chat_id)
                return web.json_response({"error": _PEER_ID_INVALID_HINT}, status=400)
            logger.exception("Failed to send relay message: %s", exc)
            return web.json_response({"error": str(exc)}, status=500)
        except Exception as exc:
            logger.exception("Failed to send relay message: %s", exc)
            return web.json_response({"error": str(exc)}, status=500)

    app.router.add_get("/health", health)
    app.router.add_post("/relay", relay)
    return app
