"""
Figma direct flow - Image download and OSS upload node.

Downloads images from Figma MCP assets and uploads to Alibaba Cloud OSS.
Replaces original URLs with permanent OSS links in the raw code.
"""
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from utils.oss import batch_upload_images_to_oss


def _normalize_asset_var_name(var_name: str) -> str:
    """Normalize image variable names (imgImage11 -> img11)."""
    m = re.match(r"^imgImage(.+)$", var_name, re.IGNORECASE)
    if m:
        suffix = m.group(1)
        normalized = suffix[0].lower() + suffix[1:]
        return f"img{normalized}"
    return var_name


def _extract_image_urls(code: str) -> List[Dict[str, str]]:
    """Extract image URLs from assets code."""
    results = []
    pattern = r"""(?:export\s+)?const\s+(img\w+)\s*=\s*["']([^"']+)["']\s*;?"""
    for m in re.finditer(pattern, code):
        var_name, url = m.group(1), m.group(2)
        if url.startswith(("http://", "https://")):
            results.append({"varName": var_name, "url": url, "fullMatch": m.group(0)})
    return results


async def _download_image(url: str) -> Optional[Dict[str, Any]]:
    """Download a single image. Returns {buffer, content_type} or None."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            if response.status_code != 200:
                print(f"[ImageDownload] Warning: Download failed ({response.status_code}): {url}")
                return None
            content_type = response.headers.get("content-type", "image/png")
            return {"buffer": response.content, "contentType": content_type}
    except Exception as e:
        print(f"[ImageDownload] Warning: Download error for {url}: {e}")
        return None


async def image_download_node(state: dict) -> dict:
    """Download Figma images and upload to OSS, replacing URLs in code."""
    print("\n" + "=" * 80)
    print("[ImageDownloadNode] Starting image processing")
    print("=" * 80)

    raw_code = state.get("figmaCode", "")
    if not raw_code:
        print("[ImageDownloadNode] No rawCode found, skipping image processing")
        return {}

    # Step 1: Extract image URLs
    print("[ImageDownloadNode] Step 1/4: Extracting image URLs...")
    image_urls = _extract_image_urls(raw_code)

    if not image_urls:
        print("[ImageDownloadNode] No image links found, skipping")
        return {}

    print(f"   Found {len(image_urls)} image links")

    # Step 2: Download images
    print(f"\n[ImageDownloadNode] Step 2/4: Downloading {len(image_urls)} images...")

    import asyncio

    async def download_one(item: Dict[str, str]):
        result = await _download_image(item["url"])
        return {**item, "downloaded": result}

    download_results = await asyncio.gather(*[download_one(img) for img in image_urls])

    successful = [r for r in download_results if r["downloaded"]]
    failed = [r for r in download_results if not r["downloaded"]]
    print(f"   Success: {len(successful)}, Failed: {len(failed)}")

    if not successful:
        print("[ImageDownloadNode] All downloads failed, keeping original links")
        return {}

    # Step 3: Upload to OSS
    print(f"\n[ImageDownloadNode] Step 3/4: Uploading {len(successful)} images to OSS...")

    upload_input = [
        {
            "buffer": r["downloaded"]["buffer"],
            "originalUrl": r["url"],
            "contentType": r["downloaded"]["contentType"],
        }
        for r in successful
    ]

    try:
        upload_results = await batch_upload_images_to_oss(upload_input)
    except Exception as e:
        print(f"[ImageDownloadNode] OSS upload failed: {e}")
        return {}

    successful_uploads = [r for r in upload_results if r.get("success")]
    print(f"   Uploaded successfully: {len(successful_uploads)}")

    # Step 4: Replace URLs in rawCode
    print(f"\n[ImageDownloadNode] Step 4/4: Replacing URLs...")
    updated_code = raw_code
    replaced_count = 0

    for result in upload_results:
        if result.get("success") and result.get("ossUrl") != result.get("originalUrl"):
            old_url = result["originalUrl"]
            new_url = result["ossUrl"]
            if old_url in updated_code:
                updated_code = updated_code.replace(old_url, new_url)
                replaced_count += 1

    print(f"   Replaced: {replaced_count} URLs")

    # Step 5: Normalize variable names
    print(f"\n[ImageDownloadNode] Step 5/5: Normalizing variable names...")
    defined_vars = set(re.findall(r"(?:export\s+)?const\s+(img\w+)\s*=", updated_code))
    rename_map = {}
    for var_name in defined_vars:
        normalized = _normalize_asset_var_name(var_name)
        if normalized != var_name and normalized not in defined_vars:
            rename_map[var_name] = normalized

    for old, new in rename_map.items():
        updated_code = re.sub(r"\b" + re.escape(old) + r"\b", new, updated_code)

    print(f"   Normalized: {len(rename_map)} variable names")

    print("\n" + "=" * 80)
    print("[ImageDownloadNode] Image processing complete")
    print(f"   Total: {len(image_urls)}, Uploaded: {len(successful_uploads)}, Failed: {len(failed)}")
    print("=" * 80 + "\n")

    return {"figmaCode": updated_code}
