import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

BUSINESS_BOT_TOKEN = os.getenv("BUSINESS_BOT_TOKEN", "")
DOWNLOADER_BOT_USER_ID = int(os.getenv("DOWNLOADER_BOT_USER_ID", "0"))
DOWNLOADER_BOT_USERNAME = os.getenv("DOWNLOADER_BOT_USERNAME", "").strip().lstrip("@")
MAIN_BOT_USER_ID = int(os.getenv("MAIN_BOT_USER_ID", "0"))


def get_downloader_chat_id() -> int | str:
    """Chat id for send_message: @username preferred, else numeric user id."""
    if DOWNLOADER_BOT_USERNAME:
        return f"@{DOWNLOADER_BOT_USERNAME}"
    return DOWNLOADER_BOT_USER_ID


BUSINESS_API_PORT = int(os.getenv("BUSINESS_API_PORT", "8898"))
BUSINESS_CONNECTION_FILE = Path(
    os.getenv("BUSINESS_CONNECTION_FILE", "data/business_connection.json"),
)
# Optional fallback if data/business_connection.json was lost after container recreate.
# Get id from business-bot logs ("Business connection enabled: id=...") or Telegram reconnect.
BUSINESS_CONNECTION_ID = os.getenv("BUSINESS_CONNECTION_ID", "").strip()
