import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

BUSINESS_BOT_TOKEN = os.getenv("BUSINESS_BOT_TOKEN", "")
RELAY_GROUP_ID = int(os.getenv("RELAY_GROUP_ID", "-1003927121595"))
BUSINESS_API_PORT = int(os.getenv("BUSINESS_API_PORT", "8898"))
BUSINESS_CONNECTION_FILE = Path(
    os.getenv("BUSINESS_CONNECTION_FILE", "data/business_connection.json"),
)
