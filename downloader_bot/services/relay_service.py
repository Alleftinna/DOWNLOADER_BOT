import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

from downloader_bot.bot.messages import MESSAGES
from downloader_bot.clients.business_relay_client import BusinessRelayClient
from downloader_bot.config import RELAY_OWNER_USER_ID, RELAY_TIMEOUT_SECONDS
from downloader_bot.infrastructure.temp_files import cleanup_temp_dir
from downloader_bot.services.download_service import DownloadService
from downloader_bot.services.video_delivery import VideoDeliveryService

logger = logging.getLogger(__name__)

MAX_CAPTION_LENGTH = 1024


@dataclass
class PendingRelay:
    message: Message
    url: str
    user_mention: str
    processing_message_id: int
    matched: bool = field(default=False)
    fallback_task: asyncio.Task | None = field(default=None, repr=False)


class RelayService:
    def __init__(
        self,
        bot: Bot,
        download_service: DownloadService,
        delivery_service: VideoDeliveryService,
        business_client: BusinessRelayClient | None = None,
    ) -> None:
        self.bot = bot
        self.download_service = download_service
        self.delivery_service = delivery_service
        self.business_client = business_client or BusinessRelayClient()
        self._queue: deque[PendingRelay] = deque()
        self._lock = asyncio.Lock()

    async def submit(
        self,
        message: Message,
        url: str,
        user_mention: str,
        processing_message_id: int,
    ) -> None:
        pending = PendingRelay(
            message=message,
            url=url,
            user_mention=user_mention,
            processing_message_id=processing_message_id,
        )

        if RELAY_OWNER_USER_ID:
            try:
                await self.bot.send_message(
                    chat_id=RELAY_OWNER_USER_ID,
                    text=format_owner_relay_message(url, user_mention, message.chat.id),
                )
            except TelegramBadRequest as exc:
                logger.warning("Could not notify owner %s: %s", RELAY_OWNER_USER_ID, exc)

        relay_ok = await self.business_client.send_url(url)
        if not relay_ok:
            logger.warning("Business relay failed for url=%s — immediate fallback", url)
            await self._run_fallback(pending)
            return

        async with self._lock:
            self._queue.append(pending)
        pending.fallback_task = asyncio.create_task(self._fallback_after_timeout(pending))
        logger.info(
            "Relay enqueued url=%s chat=%s queue_size=%s",
            url,
            message.chat.id,
            len(self._queue),
        )

    async def handle_owner_video(self, message: Message) -> bool:
        async with self._lock:
            if not self._queue:
                logger.info("Relay skip owner video: empty queue msg_id=%s", message.message_id)
                return False
            pending = self._queue.popleft()

        pending.matched = True
        if pending.fallback_task and not pending.fallback_task.done():
            pending.fallback_task.cancel()

        caption = build_relay_caption(pending.user_mention, pending.url)
        try:
            await self.bot.copy_message(
                chat_id=pending.message.chat.id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                caption=caption,
                message_thread_id=pending.message.message_thread_id,
            )
        except TelegramBadRequest as exc:
            logger.error("Relay copy_message failed: %s — running fallback", exc)
            await self._run_fallback(pending)
            return True

        await self._cleanup_after_success(pending)
        logger.info("Relay delivered url=%s to chat=%s", pending.url, pending.message.chat.id)
        return True

    async def _fallback_after_timeout(self, pending: PendingRelay) -> None:
        try:
            await asyncio.sleep(RELAY_TIMEOUT_SECONDS)
        except asyncio.CancelledError:
            return

        async with self._lock:
            if pending.matched:
                return
            try:
                self._queue.remove(pending)
            except ValueError:
                return

        logger.warning(
            "Relay timeout after %ss for url=%s chat=%s — fallback download",
            RELAY_TIMEOUT_SECONDS,
            pending.url,
            pending.message.chat.id,
        )
        await self._run_fallback(pending)

    async def _run_fallback(self, pending: PendingRelay) -> None:
        pending.matched = True
        if pending.fallback_task and not pending.fallback_task.done():
            pending.fallback_task.cancel()

        video_dir = None
        try:
            result = await self.download_service.download(pending.url)
            if result:
                video_dir = result.temp_dir
                caption = f"{MESSAGES['success'].format(result.filename)}\n{pending.user_mention}\n{pending.url}"
                await self.delivery_service.handle_video_sending(
                    pending.message,
                    result.local_path,
                    caption,
                    result.temp_dir,
                    pending.user_mention,
                    pending.url,
                )
                await pending.message.delete()
            else:
                await self.delivery_service.send_message_to_chat(
                    pending.message,
                    MESSAGES["error_download"],
                )
        except Exception as exc:
            logger.exception("Relay fallback failed for url=%s: %s", pending.url, exc)
            await self.delivery_service.send_message_to_chat(
                pending.message,
                MESSAGES["error_download"],
            )
        finally:
            await self._delete_processing_message(pending)
            cleanup_temp_dir(video_dir)

    async def _cleanup_after_success(self, pending: PendingRelay) -> None:
        try:
            await pending.message.delete()
        except TelegramBadRequest as exc:
            logger.warning("Could not delete user message: %s", exc)
        await self._delete_processing_message(pending)

    async def _delete_processing_message(self, pending: PendingRelay) -> None:
        try:
            await self.bot.delete_message(
                pending.message.chat.id,
                pending.processing_message_id,
            )
        except TelegramBadRequest as exc:
            logger.warning("Could not delete processing message: %s", exc)


def format_owner_relay_message(url: str, user_mention: str, chat_id: int) -> str:
    return f"Новая ссылка\nОт: {user_mention}\nЧат: {chat_id}\n{url}"


def build_relay_caption(user_mention: str, url: str) -> str:
    caption = f"{user_mention}\n{url}"
    if len(caption) <= MAX_CAPTION_LENGTH:
        return caption
    max_url_len = MAX_CAPTION_LENGTH - len(user_mention) - 2
    if max_url_len < 20:
        return caption[:MAX_CAPTION_LENGTH]
    return f"{user_mention}\n{url[:max_url_len]}…"
