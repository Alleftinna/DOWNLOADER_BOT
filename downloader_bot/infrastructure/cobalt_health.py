import logging

import aiohttp

from downloader_bot.config import COBALT_API_KEY, COBALT_API_URL, VIDEO_QUALITY


async def check_cobalt_reachable() -> tuple[bool, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if COBALT_API_KEY:
        headers["Authorization"] = f"Api-Key {COBALT_API_KEY}"

    payload = {
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "videoQuality": VIDEO_QUALITY,
        "alwaysProxy": True,
    }

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(COBALT_API_URL, json=payload, headers=headers) as response:
                body = await response.text()
                if response.status >= 500:
                    return False, f"HTTP {response.status}: {body[:200]}"
                return True, f"HTTP {response.status}: {body[:200]}"
    except aiohttp.ClientConnectorError as exc:
        return False, f"connection error ({type(exc).__name__}): {exc}"
    except TimeoutError:
        return False, "timeout connecting to Cobalt"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
