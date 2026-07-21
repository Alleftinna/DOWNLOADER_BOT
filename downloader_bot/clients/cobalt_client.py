import logging
import os

import aiofiles
import aiohttp

from downloader_bot.config import COBALT_API_KEY, COBALT_API_URL, VIDEO_QUALITY
from downloader_bot.infrastructure.temp_files import cleanup_temp_dir, create_video_temp_dir
from downloader_bot.media.ffmpeg import bytes_to_mb
from downloader_bot.models import DownloadResult, VideoInfo


class CobaltClient:
    def __init__(
        self,
        api_url: str = COBALT_API_URL,
        api_key: str = COBALT_API_KEY,
        video_quality: str = VIDEO_QUALITY,
    ) -> None:
        self.api_url = api_url
        self.api_key = api_key
        self.video_quality = video_quality

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Api-Key {self.api_key}"
        return headers

    def _payload(self, url: str) -> dict[str, object]:
        return {
            "url": url,
            "videoQuality": self.video_quality,
            "audioFormat": "mp3",
            "filenameStyle": "basic",
            "alwaysProxy": True,
        }

    @staticmethod
    def _ensure_mp4(filename: str | None) -> str:
        filename = filename or "video.mp4"
        if filename.lower().endswith(".mp4"):
            return filename
        stem = filename.rsplit(".", 1)[0] if "." in filename else filename
        return f"{stem}.mp4"

    async def download(self, url: str) -> DownloadResult | None:
        video_dir = create_video_temp_dir()
        try:
            logging.info("Sending request to cobalt-api at %s", self.api_url)
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=self._payload(url), headers=self._headers()) as response:
                    result = await response.json()

                if result.get("status") == "error":
                    logging.error("Cobalt error while downloading: %s", result.get("error", {}))
                    cleanup_temp_dir(video_dir)
                    return None

                if result.get("status") not in ["tunnel", "redirect"]:
                    logging.error("Unexpected cobalt response status: %s", result.get("status"))
                    cleanup_temp_dir(video_dir)
                    return None

                download_url = result.get("url")
                if not download_url:
                    logging.error("Cobalt response did not include a download URL")
                    cleanup_temp_dir(video_dir)
                    return None

                filename = self._ensure_mp4(result.get("filename"))
                local_path = os.path.join(video_dir, filename)

                async with session.get(download_url) as file_response:
                    if file_response.status != 200:
                        logging.error("Error downloading cobalt file: HTTP %s", file_response.status)
                        cleanup_temp_dir(video_dir)
                        return None
                    async with aiofiles.open(local_path, "wb") as file_obj:
                        await file_obj.write(await file_response.read())

                file_size = os.path.getsize(local_path)
                if file_size <= 0:
                    logging.error("Downloaded cobalt file is empty")
                    cleanup_temp_dir(video_dir)
                    return None

                logging.info("Downloaded cobalt file size: %.2fMB", bytes_to_mb(file_size))
                return DownloadResult(local_path=local_path, filename=filename, temp_dir=video_dir, source="cobalt")
        except aiohttp.ClientConnectorError as exc:
            logging.error(
                "Cobalt connection failed at %s (%s): %s. "
                "Check that bot and cobalt-api share the same Docker network and COBALT_API_URL is correct.",
                self.api_url,
                type(exc).__name__,
                exc,
            )
            cleanup_temp_dir(video_dir)
            return None
        except Exception as exc:
            logging.error("Error during cobalt download at %s (%s): %s", self.api_url, type(exc).__name__, exc)
            cleanup_temp_dir(video_dir)
            return None

    async def get_video_info(self, url: str) -> VideoInfo | None:
        try:
            logging.info("Requesting direct URL from cobalt-api at %s", self.api_url)
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=self._payload(url), headers=self._headers()) as response:
                    result = await response.json()

            if result.get("status") == "error":
                logging.error("Cobalt error while getting info: %s", result.get("error", {}))
                return None

            if result.get("status") not in ["tunnel", "redirect"]:
                logging.error("Unexpected cobalt status for inline: %s", result.get("status"))
                return None

            direct_url = result.get("url")
            if not direct_url:
                return None
            return VideoInfo(
                direct_url=direct_url,
                thumbnail_url=result.get("thumbnail") or result.get("thumb"),
                filename=self._ensure_mp4(result.get("filename")),
                source="cobalt",
            )
        except aiohttp.ClientConnectorError as exc:
            logging.error(
                "Cobalt connection failed at %s (%s): %s",
                self.api_url,
                type(exc).__name__,
                exc,
            )
            return None
        except Exception as exc:
            logging.error("Error getting cobalt direct url at %s (%s): %s", self.api_url, type(exc).__name__, exc)
            return None
