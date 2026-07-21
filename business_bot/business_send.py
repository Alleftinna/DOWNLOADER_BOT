from aiogram import Bot
from aiogram.types import Message


async def send_business_media_copy(
    bot: Bot,
    *,
    chat_id: int,
    message: Message,
    business_connection_id: str,
) -> Message:
    """Re-send media to a chat on behalf of the business account owner."""
    kwargs = {
        "chat_id": chat_id,
        "business_connection_id": business_connection_id,
        "caption": message.caption,
    }

    if message.video:
        return await bot.send_video(video=message.video.file_id, **kwargs)
    if message.document:
        return await bot.send_document(document=message.document.file_id, **kwargs)
    if message.animation:
        return await bot.send_animation(animation=message.animation.file_id, **kwargs)
    if message.video_note:
        return await bot.send_video_note(
            chat_id=chat_id,
            video_note=message.video_note.file_id,
            business_connection_id=business_connection_id,
        )

    raise ValueError("message has no supported media type")
