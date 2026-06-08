"""
Alibaba Cloud OSS utility using oss2 library.
"""
import hashlib
import io
import os
from datetime import datetime
from typing import Optional

import oss2

from config.oss import oss_config

# Singleton OSS bucket
_oss_bucket: Optional[oss2.Bucket] = None


def get_oss_client() -> oss2.Bucket:
    """Get OSS bucket instance (singleton)."""
    global _oss_bucket
    if _oss_bucket is None:
        if not oss_config.access_key_id or not oss_config.access_key_secret or not oss_config.bucket:
            raise RuntimeError(
                "OSS configuration incomplete. Check ALI_OSS_AK, ALI_OSS_SK, ALI_OSS_BUCKET in .env"
            )

        auth = oss2.Auth(oss_config.access_key_id, oss_config.access_key_secret)
        endpoint = oss_config.endpoint
        if oss_config.secure and not endpoint.startswith("https://"):
            endpoint = f"https://{endpoint}"
        elif not oss_config.secure and not endpoint.startswith("http://"):
            endpoint = f"http://{endpoint}"

        _oss_bucket = oss2.Bucket(auth, endpoint, oss_config.bucket)

    return _oss_bucket


def _get_ext_from_content_type(content_type: str) -> str:
    type_map = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/gif": "gif",
        "image/webp": "webp",
        "image/svg+xml": "svg",
        "image/bmp": "bmp",
    }
    return type_map.get(content_type.lower(), "png")


def _get_ext_from_url(url: str) -> str:
    import re
    match = re.search(r"\.([a-zA-Z0-9]+)(?:\?|$)", url)
    if match:
        ext = match.group(1).lower()
        if ext in {"png", "jpg", "jpeg", "gif", "webp", "svg", "bmp"}:
            return "jpg" if ext == "jpeg" else ext
    return "png"


async def upload_image_to_oss(
    data: bytes,
    original_url: Optional[str] = None,
    content_type: Optional[str] = None,
    file_name: Optional[str] = None,
) -> str:
    """Upload image bytes to OSS and return public URL."""
    client = get_oss_client()

    # Determine extension
    ext = "png"
    if content_type:
        ext = _get_ext_from_content_type(content_type)
    elif original_url:
        ext = _get_ext_from_url(original_url)

    # Generate filename using content hash
    content_hash = hashlib.md5(data).hexdigest()[:12]
    timestamp = int(datetime.now().timestamp() * 1000)
    fname = file_name or f"{timestamp}-{content_hash}"

    date_str = datetime.now().strftime("%Y-%m-%d")
    oss_path = f"figma-images/{date_str}/{fname}.{ext}"

    # Upload
    ct = content_type or f"image/{'svg+xml' if ext == 'svg' else ext}"
    client.put_object(oss_path, io.BytesIO(data), headers={"Content-Type": ct})

    public_url = f"https://{oss_config.bucket}.{oss_config.endpoint}/{oss_path}"
    return public_url


async def batch_upload_images_to_oss(
    images: list[dict],
) -> list[dict]:
    """
    Batch upload images to OSS.
    Each image dict: {buffer: bytes, original_url: str, content_type?: str}
    Returns list of {original_url, oss_url, success, error?}
    """
    import asyncio

    async def upload_one(img: dict) -> dict:
        try:
            oss_url = await upload_image_to_oss(
                img["buffer"],
                original_url=img.get("originalUrl"),
                content_type=img.get("contentType"),
            )
            return {"originalUrl": img["originalUrl"], "ossUrl": oss_url, "success": True}
        except Exception as e:
            print(f"Upload failed for {img.get('originalUrl', '')}: {e}")
            return {
                "originalUrl": img["originalUrl"],
                "ossUrl": img["originalUrl"],
                "success": False,
                "error": str(e),
            }

    results = await asyncio.gather(*[upload_one(img) for img in images])
    return list(results)
