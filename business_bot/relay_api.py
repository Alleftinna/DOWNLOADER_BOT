import logging

from aiohttp import web
from aiogram import Bot

from business_bot.config import RELAY_GROUP_ID
from business_bot.connection_store import ConnectionStore

logger = logging.getLogger(__name__)


def create_relay_app(bot: Bot, store: ConnectionStore) -> web.Application:
    app = web.Application()

    async def health(_request: web.Request) -> web.Response:
        connected = store.is_connected()
        return web.json_response(
            {
                "ok": True,
                "business_connection": connected,
                "relay_group_id": RELAY_GROUP_ID,
            }
        )

    async def relay(request: web.Request) -> web.Response:
        connection_id = store.get_connection_id()
        if not connection_id:
            return web.json_response(
                {"error": "no business connection — connect bot in Telegram Business settings"},
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
            sent = await bot.send_message(
                chat_id=RELAY_GROUP_ID,
                text=url,
                business_connection_id=connection_id,
            )
            logger.info(
                "Relay sent url=%s to group=%s msg_id=%s",
                url,
                RELAY_GROUP_ID,
                sent.message_id,
            )
            return web.json_response({"ok": True, "message_id": sent.message_id})
        except Exception as exc:
            logger.exception("Failed to send relay message: %s", exc)
            return web.json_response({"error": str(exc)}, status=500)

    app.router.add_get("/health", health)
    app.router.add_post("/relay", relay)
    return app
