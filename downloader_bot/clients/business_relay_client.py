import logging

import aiohttp

from downloader_bot.config import BUSINESS_BOT_URL

logger = logging.getLogger(__name__)


class BusinessRelayClient:
    def __init__(self, base_url: str = BUSINESS_BOT_URL) -> None:
        self.base_url = base_url.rstrip("/")

    async def send_url(self, url: str) -> bool:
        endpoint = f"{self.base_url}/relay"
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(endpoint, json={"url": url}) as response:
                    if response.status == 200:
                        return True
                    body = await response.text()
                    logger.error(
                        "Business relay failed: HTTP %s %s — %s",
                        response.status,
                        endpoint,
                        body[:500],
                    )
                    return False
        except Exception as exc:
            logger.error("Business relay request failed: %s — %s", endpoint, exc)
            return False

    async def check_health(self) -> tuple[bool, str]:
        endpoint = f"{self.base_url}/health"
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(endpoint) as response:
                    body = await response.json()
                    if response.status != 200:
                        return False, f"HTTP {response.status}"
                    if body.get("business_connection"):
                        return True, "business connection active"
                    return False, "API up but business connection not configured"
        except Exception as exc:
            return False, str(exc)
