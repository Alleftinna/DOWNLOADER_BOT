from dataclasses import dataclass


@dataclass(frozen=True)
class DownloadResult:
    local_path: str
    filename: str
    temp_dir: str
    source: str


@dataclass(frozen=True)
class VideoInfo:
    direct_url: str
    thumbnail_url: str | None
    filename: str
    source: str
