import logging
import os

from aiogram import Bot
from aiogram.types import FSInputFile, Message

from downloader_bot.bot.messages import MESSAGES
from downloader_bot.config import MAX_SINGLE_FILE_SIZE, MAX_TOTAL_FILE_SIZE
from downloader_bot.media.ffmpeg import bytes_to_mb, create_thumbnail, split_video_with_ffmpeg


class VideoDeliveryService:
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def send_message_to_chat(self, message: Message, text: str) -> None:
        await self.bot.send_message(
            chat_id=message.chat.id,
            text=text,
            message_thread_id=message.message_thread_id,
        )

    async def handle_video_sending(
        self,
        message: Message,
        file_path: str,
        caption: str,
        video_dir: str,
        user_mention: str,
        url: str,
    ) -> None:
        try:
            file_size = os.path.getsize(file_path)
            file_size_mb = bytes_to_mb(file_size)
            logging.info("File size: %.2fMB", file_size_mb)

            if file_size <= MAX_SINGLE_FILE_SIZE:
                await self.send_single_video(message, file_path, caption)
            elif file_size <= MAX_TOTAL_FILE_SIZE:
                await self.send_split_video(message, file_path, video_dir, user_mention, url)
            else:
                await self.send_message_to_chat(
                    message,
                    MESSAGES["file_extremely_large"].format(round(file_size_mb, 2)),
                )
        except Exception as exc:
            await self.send_message_to_chat(message, MESSAGES["error_send"].format(str(exc)))
            logging.error("Error sending video: %s", exc)

    async def send_single_video(self, message: Message, file_path: str, caption: str) -> None:
        video = FSInputFile(file_path)
        video_dir = os.path.dirname(file_path)
        thumbnail_path = await create_thumbnail(file_path, video_dir)

        kwargs = {
            "chat_id": message.chat.id,
            "video": video,
            "caption": caption,
            "message_thread_id": message.message_thread_id,
        }
        if thumbnail_path:
            kwargs["thumbnail"] = FSInputFile(thumbnail_path)
        await self.bot.send_video(**kwargs)

    async def send_split_video(
        self,
        message: Message,
        file_path: str,
        video_dir: str,
        user_mention: str,
        url: str,
    ) -> None:
        file_size_mb = bytes_to_mb(os.path.getsize(file_path))
        temp_msg = await self.bot.send_message(
            chat_id=message.chat.id,
            text=MESSAGES["file_too_large"].format(round(file_size_mb, 2)),
            message_thread_id=message.message_thread_id,
        )

        parts, total_parts = await split_video_with_ffmpeg(file_path, video_dir)
        await temp_msg.delete()

        if parts and total_parts > 0:
            await self.send_video_parts(message, parts, total_parts, user_mention, url)
        else:
            await self.send_message_to_chat(message, MESSAGES["splitting_error"])

    async def send_video_parts(
        self,
        message: Message,
        parts: list[str],
        total_parts: int,
        user_mention: str,
        url: str,
    ) -> None:
        for index, part_path in enumerate(parts, 1):
            part_size_mb = bytes_to_mb(os.path.getsize(part_path))
            caption = self.get_part_caption(index, total_parts, user_mention, url)
            logging.info("Sending part %s/%s, size: %.2fMB", index, total_parts, part_size_mb)
            await self.send_video_part(message, part_path, caption, index)

    @staticmethod
    def get_part_caption(part_num: int, total_parts: int, user_mention: str, url: str) -> str:
        if part_num == 1:
            return f"{MESSAGES['sending_part'].format(part_num, total_parts)}\n{user_mention}\n{url}"
        if part_num == total_parts:
            return MESSAGES["sending_complete"]
        return MESSAGES["sending_part"].format(part_num, total_parts)

    async def send_video_part(
        self,
        message: Message,
        part_path: str,
        caption: str,
        part_index: int | None = None,
    ) -> None:
        video = FSInputFile(part_path)
        video_dir = os.path.dirname(part_path)
        thumbnail_path = await create_thumbnail(part_path, video_dir, part_index)

        try:
            kwargs = {
                "chat_id": message.chat.id,
                "video": video,
                "caption": caption,
                "message_thread_id": message.message_thread_id,
            }
            if thumbnail_path:
                kwargs["thumbnail"] = FSInputFile(thumbnail_path)
            await self.bot.send_video(**kwargs)
        except Exception as exc:
            logging.error("Error sending part as video: %s, trying as document", exc)
            await self.bot.send_document(
                chat_id=message.chat.id,
                document=FSInputFile(part_path),
                caption=f"{caption} (отправлено как файл из-за ошибки)",
                message_thread_id=message.message_thread_id,
            )
