import os
import logging
import asyncio
import time
import aiohttp
import aiofiles
import math

import shutil
import subprocess
import re
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
 
from dotenv import load_dotenv, find_dotenv
 
import uuid
from pathlib import Path
from cookie_generator import CookieGenerator

# Load environment variables
load_dotenv(find_dotenv())

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create data directory if it doesn't exist
Path("data").mkdir(exist_ok=True)

# Telegram bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOADER_API_URL = os.getenv("DOWNLOADER_API_URL", "http://downloader:8899").rstrip("/")
DOWNLOAD_POLL_INTERVAL = float(os.getenv("DOWNLOAD_POLL_INTERVAL", "1.5"))
DOWNLOAD_MAX_WAIT = float(os.getenv("DOWNLOAD_MAX_WAIT", "330"))

# File size constants (in bytes)
MAX_SINGLE_FILE_SIZE = 45 * 1024 * 1024  # 45 MB 
MAX_TOTAL_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
VIDEO_QUALITY = "480"  # Fixed quality: 480p
SEGMENT_DURATION = 120  # Длительность сегмента в секундах при разрезании видео

# Supported domains
SUPPORTED_DOMAINS = [
    # Video platforms
    "youtube.com", 
    "youtu.be",
    "tiktok.com",
    "instagram.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "vimeo.com",
    "bilibili.com",
    "bluesky.com",
    "bsky.app",
    "dailymotion.com",
    "loom.com",
    "ok.ru",
    "pinterest.com",
    "pin.it",
    "reddit.com",
    "rutube.ru",
    "snapchat.com",
    "soundcloud.com",
    "streamable.com",
    "tumblr.com",
    "twitch.tv",
    "vk.com",
    "xiaohongshu.com"
]

# Bot messages
MESSAGES = {
    "welcome": "👋 Привет! Отправь мне ссылку на видео с поддерживаемых платформ, и я скачаю его для тебя.",
    "processing": "⏳ Обрабатываю твой запрос на скачивание видео...",
    "success": "{}",
    "error_download": "❌ Не удалось скачать видео. Пожалуйста, проверь ссылку и попробуй еще раз.",
    "error_send": "Ошибка при отправке видео: {}",
    "file_too_large": "Файл слишком большой ({}MB). Подготавливаю видео для отправки...",
    "file_extremely_large": "⚠️ Файл слишком большой ({}MB) и превышает лимит в 500MB. Невозможно отправить.",
    "sending_part": "{}/{}...",
    "sending_complete": "✅ Все части видео отправлены!",
    "splitting_error": "❌ Ошибка при разделении видео. Пожалуйста, попробуйте другую ссылку."
}

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Function to convert bytes to megabytes
def bytes_to_mb(bytes_size):
    return bytes_size / (1024 * 1024)

# Функция для создания временной директории для видео
def create_video_temp_dir():
    # Создаем уникальную временную директорию внутри data
    temp_dir = os.path.join("data", f"video_{uuid.uuid4().hex}")
    os.makedirs(temp_dir, exist_ok=True)
    logging.info(f"Created temporary directory: {temp_dir}")
    return temp_dir

# Функция для удаления временной директории и всех файлов в ней
def cleanup_temp_dir(temp_dir):
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logging.info(f"Removed temporary directory: {temp_dir}")
    except Exception as e:
        logging.error(f"Error removing temporary directory {temp_dir}: {e}")

# Функция для разрезания видео на части с помощью ffmpeg
async def split_video_with_ffmpeg(video_path, video_dir):
    try:
        output_pattern = os.path.join(video_dir, "part_%03d.mp4")
        
        # Проверяем общую длительность видео
        probe_cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            video_path
        ]
        
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error(f"Error getting video duration: {result.stderr}")
            return [], 0
        
        try:
            total_duration = float(result.stdout.strip())
        except (ValueError, TypeError):
            logging.error(f"Invalid duration value: {result.stdout}")
            return [], 0
        
        logging.info(f"Video duration: {total_duration} seconds")
        
        # Определяем количество частей исходя из размера файла
        file_size = os.path.getsize(video_path)
        file_size_mb = bytes_to_mb(file_size)
        logging.info(f"Video size: {file_size_mb:.2f} MB")
        
        # Считаем количество частей, округляя вверх
        max_size_mb = MAX_SINGLE_FILE_SIZE / (1024 * 1024)
        num_parts = math.ceil(file_size_mb / max_size_mb)
        logging.info(f"Number of parts needed: {num_parts}")
        
        # Определяем длительность каждой части, просто разделив общую длительность на количество частей
        segment_duration = math.floor(total_duration / num_parts)
        
        # Минимальная длительность сегмента - 30 секунд
        if segment_duration < 30:
            segment_duration = 30
            logging.info("Segment duration too small, using minimum 30 seconds")
        
        logging.info(f"Video will be split into approximately {num_parts} parts")
        logging.info(f"Using segment duration: {segment_duration} seconds")
        
        # Команда для разделения видео
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-c", "copy",  # Копируем кодеки без перекодирования
            "-map", "0",  # Копируем все потоки
            "-f", "segment",
            "-segment_time", str(segment_duration),
            "-reset_timestamps", "1",
            "-segment_format", "mp4",
            output_pattern
        ]
        
        # Запускаем ffmpeg
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logging.error(f"Error splitting video with ffmpeg: {stderr.decode()}")
            return [], 0
        
        # Получаем список сгенерированных файлов
        parts = sorted([os.path.join(video_dir, f) for f in os.listdir(video_dir) if f.startswith("part_") and f.endswith('.mp4')])
        
        # Проверяем, что все файлы не пустые
        valid_parts = []
        for part in parts:
            part_size = os.path.getsize(part)
            part_size_mb = bytes_to_mb(part_size)
            
            if part_size == 0:
                logging.error(f"Empty part file: {part}")
                continue
            
            valid_parts.append(part)
            logging.info(f"Part {len(valid_parts)}: {part_size_mb:.2f} MB")
        
        return valid_parts, len(valid_parts)
    except Exception as e:
        logging.error(f"Error in split_video_with_ffmpeg: {e}")
        return [], 0

def _target_video_height() -> int:
    raw = str(VIDEO_QUALITY).strip().lower().rstrip("p")
    try:
        return int(raw)
    except ValueError:
        return 480


def _pick_format_id(formats: list[dict], target_height: int) -> str | None:
    with_height = [f for f in formats if f.get("height") is not None]
    if not with_height:
        return None
    at_or_below = [f for f in with_height if int(f["height"]) <= target_height]
    if at_or_below:
        best = max(at_or_below, key=lambda x: int(x["height"]))
        return str(best["id"])
    lowest = min(with_height, key=lambda x: int(x["height"]))
    return str(lowest["id"])


def _safe_filename(name: str, fallback: str) -> str:
    base = os.path.basename((name or "").strip() or fallback)
    if not base or base in (".", ".."):
        return fallback
    return base


async def download_video(url: str):
    video_dir = create_video_temp_dir()
    base = DOWNLOADER_API_URL
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    timeout_short = aiohttp.ClientTimeout(total=90)
    timeout_dl = aiohttp.ClientTimeout(total=600)

    try:
        logging.info(f"Requesting video via downloader at {base}")
        async with aiohttp.ClientSession() as session:
            format_id: str | None = None
            title = ""
            try:
                async with session.post(
                    f"{base}/api/info",
                    json={"url": url},
                    headers=headers,
                    timeout=timeout_short,
                ) as info_resp:
                    if info_resp.status == 200:
                        info = await info_resp.json()
                        title = (info.get("title") or "").strip()
                        format_id = _pick_format_id(info.get("formats") or [], _target_video_height())
                    else:
                        body = await info_resp.text()
                        logging.warning("Downloader /api/info HTTP %s: %s", info_resp.status, body[:500])
            except Exception as e:
                logging.warning("Downloader /api/info failed: %s", e)

            payload: dict = {"url": url, "format": "video", "title": title}
            if format_id:
                payload["format_id"] = format_id

            async with session.post(
                f"{base}/api/download",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as dresp:
                ddata = await dresp.json(content_type=None)
                if dresp.status != 200:
                    logging.error("Downloader /api/download error: %s", ddata)
                    cleanup_temp_dir(video_dir)
                    return None, None, None
                job_id = ddata.get("job_id")
                if not job_id:
                    logging.error("Downloader /api/download missing job_id: %s", ddata)
                    cleanup_temp_dir(video_dir)
                    return None, None, None

            deadline = time.monotonic() + DOWNLOAD_MAX_WAIT
            filename = "video.mp4"
            while time.monotonic() < deadline:
                await asyncio.sleep(DOWNLOAD_POLL_INTERVAL)
                async with session.get(
                    f"{base}/api/status/{job_id}",
                    timeout=timeout_short,
                ) as sresp:
                    if sresp.status == 404:
                        logging.error("Downloader job not found: %s", job_id)
                        cleanup_temp_dir(video_dir)
                        return None, None, None
                    st = await sresp.json(content_type=None)
                status = st.get("status")
                if status == "done":
                    filename = _safe_filename(st.get("filename") or "", "video.mp4")
                    break
                if status == "error":
                    logging.error("Downloader job error: %s", st.get("error"))
                    cleanup_temp_dir(video_dir)
                    return None, None, None

            else:
                logging.error("Downloader job timed out after %s s", DOWNLOAD_MAX_WAIT)
                cleanup_temp_dir(video_dir)
                return None, None, None

            local_path = os.path.join(video_dir, filename)
            async with session.get(
                f"{base}/api/file/{job_id}",
                timeout=timeout_dl,
            ) as fresp:
                if fresp.status != 200:
                    logging.error("Downloader /api/file HTTP %s", fresp.status)
                    cleanup_temp_dir(video_dir)
                    return None, None, None
                async with aiofiles.open(local_path, "wb") as out_f:
                    async for chunk in fresp.content.iter_chunked(256 * 1024):
                        await out_f.write(chunk)

            file_size = os.path.getsize(local_path)
            if file_size <= 0:
                logging.error("Downloaded file is empty")
                cleanup_temp_dir(video_dir)
                return None, None, None
            logging.info("Downloaded file size: %.2f MB", bytes_to_mb(file_size))
            return local_path, filename, video_dir

    except Exception as e:
        logging.error("Error during download: %s", e)
        cleanup_temp_dir(video_dir)
        return None, None, None


@dp.message(Command("start", "help"))
async def send_welcome(message: Message):
    await bot.send_message(
        chat_id=message.chat.id,
        text=MESSAGES["welcome"],
        message_thread_id=message.message_thread_id
    )


# Функция для извлечения URL из текста
def extract_url_from_text(text):
    # Регулярное выражение для поиска URL
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*(?:\?[-\w%&=.]*)?\S*'
    matches = re.findall(url_pattern, text)
    
    if matches:
        # Возвращаем первую найденную ссылку
        return matches[0]
    return None

restricted_threads = [8740]
# Handle text messages with URLs
@dp.message(F.text)
async def handle_text_message(message: Message):
    text = message.text
    video_dir = None
    if message.message_thread_id in restricted_threads:
        return
    # Получаем информацию о пользователе
    user_mention = get_user_mention(message)
    

    # Simple URL detection using the SUPPORTED_DOMAINS variable
    if any(domain in text.lower() for domain in SUPPORTED_DOMAINS):
        url = extract_url_from_text(text)
        if url:
            text = url  # Используем найденную ссылку вместо всего текста
        else:
            pass
        # Отправляем промежуточное сообщение
        processing_msg = await bot.send_message(
            chat_id=message.chat.id,
            text=MESSAGES["processing"],
            message_thread_id=message.message_thread_id
        )
        
        try:
            # Download the video with fixed 480p quality
            file_path, filename, video_dir = await download_video(url)
            
            if file_path:
                # Добавляем имя пользователя к подписи видео
                caption = f"{MESSAGES['success'].format(filename)}\n{user_mention}\n{text}"
                
                # Check file size and send accordingly
                await handle_video_sending(message, file_path, caption, video_dir, user_mention, text)
                await message.delete()
            else:
                await send_message_to_chat(message, MESSAGES["error_download"])
        finally:
            # Удаляем промежуточное сообщение
            await processing_msg.delete()
            

            
            # Удаляем временную директорию со всеми файлами
            if video_dir:
                cleanup_temp_dir(video_dir)

# Вспомогательная функция для отправки сообщения в чат
async def send_message_to_chat(message: Message, text: str):
    await bot.send_message(
        chat_id=message.chat.id,
        text=text,
        message_thread_id=message.message_thread_id
    )

# Функция для получения упоминания пользователя
def get_user_mention(message: Message) -> str:
    if message.from_user:
        if message.from_user.username:
            return f"@{message.from_user.username}"
        else:
            return f"{message.from_user.full_name}"
    return ""

# Функция для обработки отправки видео в зависимости от размера
async def handle_video_sending(message: Message, file_path: str, caption: str, video_dir: str, user_mention: str, url: str):
    try:
        # Check file size
        file_size = os.path.getsize(file_path)
        file_size_mb = bytes_to_mb(file_size)
        logging.info(f"File size: {file_size_mb:.2f}MB")
        
        # Handle different file size scenarios
        if file_size <= MAX_SINGLE_FILE_SIZE:
            await send_single_video(message, file_path, caption)
        elif file_size <= MAX_TOTAL_FILE_SIZE:
            await send_split_video(message, file_path, video_dir, user_mention, url)
        else:
            # File is too large (>500MB)
            await send_message_to_chat(message, MESSAGES["file_extremely_large"].format(round(file_size_mb, 2)))
    except Exception as e:
        await send_message_to_chat(message, MESSAGES["error_send"].format(str(e)))
        logging.error(f"Error sending video: {e}")

# Функция для отправки одиночного видео
async def send_single_video(message: Message, file_path: str, caption: str):
    video = FSInputFile(file_path)
    
    # Создаем превью для видео
    video_dir = os.path.dirname(file_path)
    thumbnail_path = await create_thumbnail(file_path, video_dir)
    
    # Если превью создано успешно, используем его при отправке
    if thumbnail_path:
        thumbnail = FSInputFile(thumbnail_path)
        await bot.send_video(
            chat_id=message.chat.id,
            video=video, 
            caption=caption, 
            thumbnail=thumbnail,
            message_thread_id=message.message_thread_id
        )
    else:
        # Если не удалось создать превью, отправляем без него
        await bot.send_video(
            chat_id=message.chat.id,
            video=video, 
            caption=caption,
            message_thread_id=message.message_thread_id
        )

# Функция для отправки разделенного видео
async def send_split_video(message: Message, file_path: str, video_dir: str, user_mention: str, url: str):
    # Готовим видео к разделению на части
    file_size = os.path.getsize(file_path)
    file_size_mb = bytes_to_mb(file_size)
    
    temp_msg = await bot.send_message(
        chat_id=message.chat.id,
        text=MESSAGES["file_too_large"].format(round(file_size_mb, 2)),
        message_thread_id=message.message_thread_id
    )
    
    # Split the video using ffmpeg
    parts, total_parts = await split_video_with_ffmpeg(file_path, video_dir)
    
    # Удаляем промежуточное сообщение о разделении
    await temp_msg.delete()
    
    if parts and total_parts > 0:
        await send_video_parts(message, parts, total_parts, user_mention, url)
    else:
        await send_message_to_chat(message, MESSAGES["splitting_error"])

# Функция для отправки частей видео
async def send_video_parts(message: Message, parts: list, total_parts: int, user_mention: str, url: str):
    # Send each part as video
    for i, part_path in enumerate(parts, 1):
        # Проверяем размер файла части
        part_size = os.path.getsize(part_path)
        part_size_mb = bytes_to_mb(part_size)
        
        # Формируем подпись для части видео
        part_caption = get_part_caption(i, total_parts, user_mention, url)
            
        logging.info(f"Sending part {i}/{total_parts}, size: {part_size_mb:.2f}MB")
        await send_video_part(message, part_path, part_caption, i)

# Функция для формирования подписи части видео
def get_part_caption(part_num: int, total_parts: int, user_mention: str, url: str) -> str:
    if part_num == 1:
        return f"{MESSAGES['sending_part'].format(part_num, total_parts)}\n{user_mention}\n{url}"
    elif part_num == total_parts:
        return MESSAGES["sending_complete"]
    else:
        return MESSAGES["sending_part"].format(part_num, total_parts)

# Функция для отправки одной части видео
async def send_video_part(message: Message, part_path: str, caption: str, part_index=None):
    video = FSInputFile(part_path)
    
    # Создаем превью для части видео с уникальным именем
    video_dir = os.path.dirname(part_path)
    thumbnail_path = await create_thumbnail(part_path, video_dir, part_index)
    
    try:
        # Отправляем как видео с превью (если доступно)
        if thumbnail_path:
            thumbnail = FSInputFile(thumbnail_path)
            await bot.send_video(
                chat_id=message.chat.id,
                video=video, 
                caption=caption, 
                thumbnail=thumbnail,
                message_thread_id=message.message_thread_id
            )
        else:
            await bot.send_video(
                chat_id=message.chat.id,
                video=video, 
                caption=caption,
                message_thread_id=message.message_thread_id
            )
    except Exception as e:
        logging.error(f"Error sending part as video: {e}, trying as document")
        # Если не удалось отправить как видео, отправляем как документ
        doc = FSInputFile(part_path)
        await bot.send_document(
            chat_id=message.chat.id,
            document=doc, 
            caption=f"{caption} (отправлено как файл из-за ошибки)",
            message_thread_id=message.message_thread_id
        )

# Функция для создания превью из видео с помощью ffmpeg
async def create_thumbnail(video_path, video_dir, unique_suffix=None):
    # Создаем уникальное имя для превью, если указан суффикс
    if unique_suffix is not None:
        thumbnail_path = os.path.join(video_dir, f"thumbnail_{unique_suffix}.jpg")
    else:
        thumbnail_path = os.path.join(video_dir, "thumbnail.jpg")
        
    try:
        # Команда ffmpeg для создания превью из середины видео
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-ss", "00:00:03",  # Берем кадр с 3-й секунды
            "-frames:v", "1",   # Только один кадр
            "-q:v", "2",        # Высокое качество
            "-f", "image2",     # Формат изображения
            thumbnail_path
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logging.error(f"Error creating thumbnail: {stderr.decode()}")
            return None
        
        # Проверяем, что превью создано и не пустое
        if os.path.exists(thumbnail_path) and os.path.getsize(thumbnail_path) > 0:
            logging.info(f"Created thumbnail: {thumbnail_path}")
            return thumbnail_path
        else:
            logging.error("Thumbnail file is empty or not created")
            return None
    except Exception as e:
        logging.error(f"Error in create_thumbnail: {e}")
        return None

async def main():
    # Start the bot
    logging.info("Starting bot...")
    
    # Инициализируем генератор куков
    try:
        cookie_generator = CookieGenerator()
        cookie_generator.start()
        logging.info("Cookie generator started successfully")
    except Exception as e:
        logging.error(f"Error starting cookie generator: {e}")
    
    # Очищаем папку data перед запуском
    try:
        data_path = Path("data")
        if data_path.exists():
            # Удаляем все файлы и подпапки в директории data
            for item in data_path.glob("*"):
                if item.is_file():
                    item.unlink()  # Удаляем файл
                elif item.is_dir():
                    shutil.rmtree(item)  # Удаляем директорию с содержимым
            logging.info("Successfully cleaned data directory")
    except Exception as e:
        logging.error(f"Error cleaning data directory: {e}")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 
