import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv


load_dotenv(find_dotenv())


def _parse_int_list(value: str) -> list[int]:
    result: list[int] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            result.append(int(item))
        except ValueError:
            continue
    return result


BOT_TOKEN = os.getenv("BOT_TOKEN")

COBALT_API_URL = os.getenv("COBALT_API_URL", "http://cobalt-api:9000")
COBALT_API_KEY = os.getenv("COBALT_API_KEY", "")
DOWNLOADER_URL = os.getenv("DOWNLOADER_URL", "http://downloader:8899")

VIDEO_QUALITY = os.getenv("VIDEO_QUALITY", "480")
SEGMENT_DURATION = int(os.getenv("SEGMENT_DURATION", "120"))

MAX_SINGLE_FILE_SIZE = int(os.getenv("MAX_SINGLE_FILE_SIZE_MB", "45")) * 1024 * 1024
MAX_TOTAL_FILE_SIZE = int(os.getenv("MAX_TOTAL_FILE_SIZE_MB", "500")) * 1024 * 1024

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
COOKIES_SAVE_PATH = os.getenv("COOKIES_SAVE_PATH", "/root/cobalt/cookies.json")
COOKIE_UPDATE_INTERVAL_HOURS = int(os.getenv("COOKIE_UPDATE_INTERVAL_HOURS", "12"))

RESTRICTED_THREADS = _parse_int_list(os.getenv("RESTRICTED_THREADS", "8740"))

DOWNLOADER_POLL_INTERVAL_SECONDS = float(os.getenv("DOWNLOADER_POLL_INTERVAL_SECONDS", "2"))
DOWNLOADER_TIMEOUT_SECONDS = float(os.getenv("DOWNLOADER_TIMEOUT_SECONDS", "300"))

YTDLP_COOKIES_FILE = os.getenv("YTDLP_COOKIES_FILE", "")

RELAY_TIMEOUT_SECONDS = int(os.getenv("RELAY_TIMEOUT_SECONDS", "120"))
RELAY_OWNER_USER_ID = int(os.getenv("RELAY_OWNER_USER_ID", "0"))
# Main bot responds only in this group (e.g. -1002185211541) and owner private chat.
ALLOWED_GROUP_ID = int(os.getenv("ALLOWED_GROUP_ID", "0"))
BUSINESS_BOT_URL = os.getenv("BUSINESS_BOT_URL", "http://business-bot:8898")
