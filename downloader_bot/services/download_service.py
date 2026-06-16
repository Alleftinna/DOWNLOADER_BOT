import logging

from downloader_bot.clients.cobalt_client import CobaltClient
from downloader_bot.clients.ytdlp_client import YtdlpClient
from downloader_bot.models import DownloadResult, VideoInfo


class DownloadService:
    def __init__(self, cobalt_client: CobaltClient, ytdlp_client: YtdlpClient) -> None:
        self.cobalt_client = cobalt_client
        self.ytdlp_client = ytdlp_client

    async def download(self, url: str) -> DownloadResult | None:
        cobalt_result = await self.cobalt_client.download(url)
        if cobalt_result:
            logging.info("Download succeeded through %s", cobalt_result.source)
            return cobalt_result

        logging.info("Cobalt download failed, trying downloader fallback")
        fallback_result = await self.ytdlp_client.download(url)
        if fallback_result:
            logging.info("Download succeeded through %s", fallback_result.source)
        return fallback_result

    async def get_video_info(self, url: str) -> VideoInfo | None:
        cobalt_info = await self.cobalt_client.get_video_info(url)
        if cobalt_info:
            return cobalt_info

        logging.info("Cobalt info failed, trying downloader fallback")
        return await self.ytdlp_client.get_video_info(url)
