import asyncio
import logging
import os
import time

import aiofiles
import aiohttp

from downloader_bot.config import (
    DOWNLOADER_POLL_INTERVAL_SECONDS,
    DOWNLOADER_TIMEOUT_SECONDS,
    DOWNLOADER_URL,
    VIDEO_QUALITY,
)
from downloader_bot.infrastructure.temp_files import cleanup_temp_dir, create_video_temp_dir
from downloader_bot.models import DownloadResult, VideoInfo


class YtdlpClient:
    def __init__(
        self,
        base_url: str = DOWNLOADER_URL,
        timeout_seconds: float = DOWNLOADER_TIMEOUT_SECONDS,
        poll_interval_seconds: float = DOWNLOADER_POLL_INTERVAL_SECONDS,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds

    async def get_info(self, url: str) -> dict | None:
        try:
            logging.info("Fallback downloader: POST %s/api/info", self.base_url)
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/api/info", json={"url": url}) as response:
                    payload = await response.json()
                    if response.status >= 400:
                        logging.warning(
                            "Fallback downloader /api/info HTTP %s: %s",
                            response.status,
                            payload.get("error", payload),
                        )
                        return None
                    return payload
        except Exception as exc:
            logging.error("Fallback downloader info request failed (%s): %s", type(exc).__name__, exc)
            return None

    async def get_video_info(self, url: str) -> VideoInfo | None:
        info = await self.get_info(url)
        if not info:
            return None
        direct_url = info.get("direct_url")
        if not direct_url:
            return None
        return VideoInfo(
            direct_url=direct_url,
            thumbnail_url=info.get("thumbnail"),
            filename=(info.get("title") or "video") + ".mp4",
            source="downloader",
        )

    async def download(self, url: str) -> DownloadResult | None:
        video_dir = create_video_temp_dir()
        try:
            logging.info("Fallback downloader: starting download for %s", url)
            info = await self.get_info(url) or {}
            format_id = self._select_format_id(info)
            title = info.get("title", "")
            payload = {
                "url": url,
                "format": "video",
                "format_id": format_id,
                "title": title,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/api/download", json=payload) as response:
                    start_payload = await response.json()
                    if response.status >= 400:
                        logging.error("Downloader start error: %s", start_payload.get("error", start_payload))
                        cleanup_temp_dir(video_dir)
                        return None
                    job_id = start_payload.get("job_id")

                if not job_id:
                    logging.error("Downloader did not return a job id")
                    cleanup_temp_dir(video_dir)
                    return None

                status = await self._wait_for_job(session, job_id)
                if not status or status.get("status") != "done":
                    logging.error("Downloader job failed: %s", status)
                    cleanup_temp_dir(video_dir)
                    return None

                filename = status.get("filename") or f"{job_id}.mp4"
                local_path = os.path.join(video_dir, filename)
                async with session.get(f"{self.base_url}/api/file/{job_id}") as file_response:
                    if file_response.status != 200:
                        logging.error("Downloader file error: HTTP %s", file_response.status)
                        cleanup_temp_dir(video_dir)
                        return None
                    async with aiofiles.open(local_path, "wb") as file_obj:
                        async for chunk in file_response.content.iter_chunked(1024 * 1024):
                            await file_obj.write(chunk)

            if not os.path.exists(local_path) or os.path.getsize(local_path) <= 0:
                logging.error("Downloader file is empty or missing")
                cleanup_temp_dir(video_dir)
                return None

            return DownloadResult(local_path=local_path, filename=filename, temp_dir=video_dir, source="downloader")
        except Exception as exc:
            logging.error("Error during downloader fallback: %s", exc)
            cleanup_temp_dir(video_dir)
            return None

    async def _wait_for_job(self, session: aiohttp.ClientSession, job_id: str) -> dict | None:
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            async with session.get(f"{self.base_url}/api/status/{job_id}") as response:
                payload = await response.json()
                if response.status >= 400:
                    return payload
                if payload.get("status") in {"done", "error"}:
                    return payload
            await asyncio.sleep(self.poll_interval_seconds)
        return {"status": "error", "error": "Downloader timed out"}

    @staticmethod
    def _select_format_id(info: dict) -> str | None:
        formats = info.get("formats") or []
        target_height = int(VIDEO_QUALITY) if VIDEO_QUALITY.isdigit() else None
        if not formats:
            return None
        if target_height:
            sorted_formats = sorted(formats, key=lambda item: abs((item.get("height") or 0) - target_height))
            return sorted_formats[0].get("id")
        return formats[0].get("id")
