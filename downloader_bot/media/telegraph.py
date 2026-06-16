import logging
import os

import aiofiles
import aiohttp


async def upload_image_to_telegra_ph(file_path: str) -> str | None:
    try:
        form = aiohttp.FormData()
        async with aiofiles.open(file_path, "rb") as file_obj:
            content = await file_obj.read()
        form.add_field(
            name="file",
            value=content,
            filename=os.path.basename(file_path),
            content_type="image/jpeg",
        )
        async with aiohttp.ClientSession() as session:
            async with session.post("https://telegra.ph/upload", data=form) as response:
                if response.status != 200:
                    logging.error("Telegraph upload failed: HTTP %s", response.status)
                    return None
                payload = await response.json()
                if isinstance(payload, list) and payload and isinstance(payload[0], dict):
                    src = payload[0].get("src")
                    if src:
                        return "https://telegra.ph" + src
                logging.error("Unexpected telegraph response: %s", payload)
                return None
    except Exception as exc:
        logging.error("Error uploading to telegra.ph: %s", exc)
        return None
