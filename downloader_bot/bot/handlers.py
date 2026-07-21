import logging
import re
import urllib.parse
import uuid

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultVideo,
    InputTextMessageContent,
    Message,
)

from downloader_bot.bot.messages import MESSAGES, SUPPORTED_DOMAINS
from downloader_bot.config import RESTRICTED_THREADS
from downloader_bot.infrastructure.temp_files import cleanup_temp_dir, create_video_temp_dir
from downloader_bot.media.ffmpeg import create_first_frame_thumbnail_from_remote
from downloader_bot.media.telegraph import upload_image_to_telegra_ph
from downloader_bot.services.download_service import DownloadService
from downloader_bot.services.relay_service import RelayService
from downloader_bot.services.video_delivery import VideoDeliveryService


def register_handlers(
    dp: Dispatcher,
    bot: Bot,
    download_service: DownloadService,
    delivery_service: VideoDeliveryService,
    relay_service: RelayService,
) -> None:
    @dp.message(Command("start", "help"))
    async def send_welcome(message: Message) -> None:
        await bot.send_message(
            chat_id=message.chat.id,
            text=MESSAGES["welcome"],
            message_thread_id=message.message_thread_id,
        )

    @dp.inline_query()
    async def inline_video_handler(query: InlineQuery) -> None:
        text = (query.query or "").strip()
        if not text:
            await query.answer([], is_personal=True, cache_time=1)
            return

        url = extract_url_from_text(text) or text
        if not is_supported_url(url):
            await query.answer([], is_personal=True, cache_time=1)
            return

        info = await download_service.get_video_info(url)
        video_url = sanitize_http_url(info.direct_url) if info else None
        thumb_url = sanitize_http_url(info.thumbnail_url) if info and info.thumbnail_url else None
        if not thumb_url or not thumb_url.lower().endswith((".jpg", ".jpeg")):
            thumb_url = "https://telegra.ph/file/6c0a7e38485639b61436a.jpg"

        if video_url:
            temp_dir = create_video_temp_dir("inline")
            local_thumb = await create_first_frame_thumbnail_from_remote(video_url, temp_dir)
            if local_thumb:
                uploaded_thumb = await upload_image_to_telegra_ph(local_thumb)
                if uploaded_thumb:
                    thumb_url = uploaded_thumb
            cleanup_temp_dir(temp_dir)

            result = InlineQueryResultVideo(
                id=str(uuid.uuid4()),
                video_url=video_url,
                mime_type="video/mp4",
                thumbnail_url=thumb_url,
                title="Video",
            )
            try:
                await query.answer([result], is_personal=True, cache_time=1)
            except TelegramBadRequest as exc:
                logging.error("Inline answer failed: %s", exc)
                await query.answer([_inline_error_result()], is_personal=True, cache_time=1)
        else:
            await query.answer([_inline_error_result()], is_personal=True, cache_time=1)

    @dp.message(F.text)
    async def handle_text_message(message: Message) -> None:
        text = message.text or ""
        if message.message_thread_id in RESTRICTED_THREADS:
            return
        if not is_supported_url(text):
            return

        url = extract_url_from_text(text) or text
        user_mention = get_user_mention(message)
        processing_msg = await bot.send_message(
            chat_id=message.chat.id,
            text=MESSAGES["processing"],
            message_thread_id=message.message_thread_id,
        )

        try:
            await relay_service.submit(
                message=message,
                url=url,
                user_mention=user_mention,
                processing_message_id=processing_msg.message_id,
            )
        except Exception as exc:
            logging.exception("Relay submit failed: %s", exc)
            await delivery_service.send_message_to_chat(message, MESSAGES["error_download"])
            await processing_msg.delete()


def extract_url_from_text(text: str) -> str | None:
    url_pattern = r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*(?:\?[-\w%&=.]*)?\S*"
    matches = re.findall(url_pattern, text)
    return matches[0] if matches else None


def is_supported_url(text: str) -> bool:
    return any(domain in text.lower() for domain in SUPPORTED_DOMAINS)


def get_user_mention(message: Message) -> str:
    if message.from_user:
        if message.from_user.username:
            return f"@{message.from_user.username}"
        return message.from_user.full_name
    return ""


def sanitize_http_url(raw_url: str | None) -> str | None:
    if not raw_url or not isinstance(raw_url, str):
        return None
    raw_url = raw_url.strip().splitlines()[0].replace("&amp;", "&")
    if not raw_url.lower().startswith(("http://", "https://")):
        return None
    try:
        parts = urllib.parse.urlsplit(raw_url)
        scheme = "https" if parts.scheme not in ("http", "https") or parts.scheme == "http" else parts.scheme
        try:
            netloc = parts.netloc.encode("idna").decode("ascii")
        except Exception:
            netloc = parts.netloc
        safe_path = urllib.parse.quote(parts.path, safe="/:@-._~!$&'()*+,;=")
        query_pairs = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        safe_query = "&".join(
            f"{urllib.parse.quote(key, safe='-._~')}={urllib.parse.quote(value, safe='-._~/:@!$&' + chr(39) + '()*+,;=')}"
            for key, value in query_pairs
        )
        return urllib.parse.urlunsplit((scheme, netloc, safe_path, safe_query, ""))
    except Exception:
        return None


def _inline_error_result() -> InlineQueryResultArticle:
    return InlineQueryResultArticle(
        id=str(uuid.uuid4()),
        title="Ошибка",
        description="Не удалось скачать видео",
        input_message_content=InputTextMessageContent(message_text=MESSAGES["error_download"]),
    )
