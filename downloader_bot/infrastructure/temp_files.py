import logging
import shutil
import uuid

from downloader_bot.config import DATA_DIR


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(exist_ok=True)


def create_video_temp_dir(prefix: str = "video") -> str:
    ensure_data_dir()
    temp_dir = DATA_DIR / f"{prefix}_{uuid.uuid4().hex}"
    temp_dir.mkdir(exist_ok=True)
    logging.info("Created temporary directory: %s", temp_dir)
    return str(temp_dir)


def cleanup_temp_dir(temp_dir: str | None) -> None:
    if not temp_dir:
        return
    try:
        path = DATA_DIR.parent / temp_dir if not temp_dir.startswith("/") else None
        target = path if path is not None and path.exists() else temp_dir
        shutil.rmtree(target, ignore_errors=False)
        logging.info("Removed temporary directory: %s", temp_dir)
    except FileNotFoundError:
        return
    except Exception as exc:
        logging.error("Error removing temporary directory %s: %s", temp_dir, exc)


def clean_data_dir() -> None:
    ensure_data_dir()
    for item in DATA_DIR.glob("*"):
        try:
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        except Exception as exc:
            logging.error("Error cleaning %s: %s", item, exc)
