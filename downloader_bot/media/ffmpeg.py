import logging
import math
import os
import subprocess

from downloader_bot.config import MAX_SINGLE_FILE_SIZE


def bytes_to_mb(bytes_size: int) -> float:
    return bytes_size / (1024 * 1024)


async def split_video_with_ffmpeg(video_path: str, video_dir: str) -> tuple[list[str], int]:
    try:
        output_pattern = os.path.join(video_dir, "part_%03d.mp4")
        probe_cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_path,
        ]

        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logging.error("Error getting video duration: %s", result.stderr)
            return [], 0

        try:
            total_duration = float(result.stdout.strip())
        except (ValueError, TypeError):
            logging.error("Invalid duration value: %s", result.stdout)
            return [], 0

        file_size = os.path.getsize(video_path)
        file_size_mb = bytes_to_mb(file_size)
        max_size_mb = MAX_SINGLE_FILE_SIZE / (1024 * 1024)
        num_parts = math.ceil(file_size_mb / max_size_mb)
        segment_duration = math.floor(total_duration / num_parts)
        if segment_duration < 30:
            segment_duration = 30

        cmd = [
            "ffmpeg",
            "-i",
            video_path,
            "-c",
            "copy",
            "-map",
            "0",
            "-f",
            "segment",
            "-segment_time",
            str(segment_duration),
            "-reset_timestamps",
            "1",
            "-segment_format",
            "mp4",
            output_pattern,
        ]

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, stderr = process.communicate()
        if process.returncode != 0:
            logging.error("Error splitting video with ffmpeg: %s", stderr.decode())
            return [], 0

        parts = sorted(
            os.path.join(video_dir, file_name)
            for file_name in os.listdir(video_dir)
            if file_name.startswith("part_") and file_name.endswith(".mp4")
        )
        valid_parts = [part for part in parts if os.path.getsize(part) > 0]
        return valid_parts, len(valid_parts)
    except Exception as exc:
        logging.error("Error in split_video_with_ffmpeg: %s", exc)
        return [], 0


async def create_thumbnail(video_path: str, video_dir: str, unique_suffix: int | None = None) -> str | None:
    thumbnail_name = f"thumbnail_{unique_suffix}.jpg" if unique_suffix is not None else "thumbnail.jpg"
    thumbnail_path = os.path.join(video_dir, thumbnail_name)

    try:
        cmd = [
            "ffmpeg",
            "-i",
            video_path,
            "-ss",
            "00:00:03",
            "-frames:v",
            "1",
            "-q:v",
            "2",
            "-f",
            "image2",
            thumbnail_path,
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, stderr = process.communicate()
        if process.returncode != 0:
            logging.error("Error creating thumbnail: %s", stderr.decode())
            return None

        if os.path.exists(thumbnail_path) and os.path.getsize(thumbnail_path) > 0:
            return thumbnail_path
        logging.error("Thumbnail file is empty or not created")
        return None
    except Exception as exc:
        logging.error("Error in create_thumbnail: %s", exc)
        return None


async def create_first_frame_thumbnail_from_remote(video_url: str, temp_dir: str) -> str | None:
    try:
        os.makedirs(temp_dir, exist_ok=True)
        thumbnail_path = os.path.join(temp_dir, "inline_thumbnail.jpg")
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_url,
            "-frames:v",
            "1",
            "-q:v",
            "2",
            "-f",
            "image2",
            thumbnail_path,
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, stderr = process.communicate()
        if process.returncode != 0:
            logging.error("Error creating inline thumbnail: %s", stderr.decode())
            return None

        if os.path.exists(thumbnail_path) and os.path.getsize(thumbnail_path) > 0:
            return thumbnail_path
        logging.error("Inline thumbnail file is empty or not created")
        return None
    except Exception as exc:
        logging.error("Error in create_first_frame_thumbnail_from_remote: %s", exc)
        return None
