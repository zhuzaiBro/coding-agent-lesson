"""
Figma 直连流程 - 图片下载与 OSS 上传节点。

从 Figma MCP 导出的资源链接下载图片，上传至阿里云 OSS，
并将原始代码中的临时 URL 替换为永久 OSS 链接。
"""
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from utils.oss import batch_upload_images_to_oss


def _normalize_asset_var_name(var_name: str) -> str:
    """规范化图片变量名（如 imgImage11 -> img11）。"""
    m = re.match(r"^imgImage(.+)$", var_name, re.IGNORECASE)
    if m:
        suffix = m.group(1)
        normalized = suffix[0].lower() + suffix[1:]
        return f"img{normalized}"
    return var_name


def _extract_image_urls(code: str) -> List[Dict[str, str]]:
    """从 assets 代码中提取图片 URL。"""
    results = []
    pattern = r"""(?:export\s+)?const\s+(img\w+)\s*=\s*["']([^"']+)["']\s*;?"""
    for m in re.finditer(pattern, code):
        var_name, url = m.group(1), m.group(2)
        if url.startswith(("http://", "https://")):
            results.append({"varName": var_name, "url": url, "fullMatch": m.group(0)})
    return results


async def _download_image(url: str) -> Optional[Dict[str, Any]]:
    """下载单张图片，返回 {buffer, content_type} 或 None。"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            if response.status_code != 200:
                print(f"[ImageDownload] 警告: 下载失败 ({response.status_code}): {url}")
                return None
            content_type = response.headers.get("content-type", "image/png")
            return {"buffer": response.content, "contentType": content_type}
    except Exception as e:
        print(f"[ImageDownload] 警告: 下载出错 {url}: {e}")
        return None


async def image_download_node(state: dict) -> dict:
    """下载 Figma 图片并上传 OSS，替换代码中的 URL。"""
    print("\n" + "=" * 80)
    print("[ImageDownloadNode] 开始处理图片")
    print("=" * 80)

    raw_code = state.get("figmaCode", "")
    if not raw_code:
        print("[ImageDownloadNode] 未找到 figmaCode，跳过图片处理")
        return {}

    # 步骤 1：提取图片 URL
    print("[ImageDownloadNode] 步骤 1/4: 提取图片 URL...")
    image_urls = _extract_image_urls(raw_code)

    if not image_urls:
        print("[ImageDownloadNode] 未找到图片链接，跳过")
        return {}

    print(f"   共发现 {len(image_urls)} 个图片链接")

    # 步骤 2：下载图片
    print(f"\n[ImageDownloadNode] 步骤 2/4: 下载 {len(image_urls)} 张图片...")

    import asyncio

    async def download_one(item: Dict[str, str]):
        result = await _download_image(item["url"])
        return {**item, "downloaded": result}

    download_results = await asyncio.gather(*[download_one(img) for img in image_urls])

    successful = [r for r in download_results if r["downloaded"]]
    failed = [r for r in download_results if not r["downloaded"]]
    print(f"   成功: {len(successful)}，失败: {len(failed)}")

    if not successful:
        print("[ImageDownloadNode] 全部下载失败，保留原始链接")
        return {}

    # 步骤 3：上传至 OSS
    print(f"\n[ImageDownloadNode] 步骤 3/4: 上传 {len(successful)} 张图片至 OSS...")

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
        print(f"[ImageDownloadNode] OSS 上传失败: {e}")
        return {}

    successful_uploads = [r for r in upload_results if r.get("success")]
    print(f"   上传成功: {len(successful_uploads)}")

    # 步骤 4：替换代码中的 URL
    print(f"\n[ImageDownloadNode] 步骤 4/4: 替换 URL...")
    updated_code = raw_code
    replaced_count = 0

    for result in upload_results:
        if result.get("success") and result.get("ossUrl") != result.get("originalUrl"):
            old_url = result["originalUrl"]
            new_url = result["ossUrl"]
            if old_url in updated_code:
                updated_code = updated_code.replace(old_url, new_url)
                replaced_count += 1

    print(f"   已替换: {replaced_count} 个 URL")

    # 步骤 5：规范化变量名
    print(f"\n[ImageDownloadNode] 步骤 5/5: 规范化变量名...")
    defined_vars = set(re.findall(r"(?:export\s+)?const\s+(img\w+)\s*=", updated_code))
    rename_map = {}
    for var_name in defined_vars:
        normalized = _normalize_asset_var_name(var_name)
        if normalized != var_name and normalized not in defined_vars:
            rename_map[var_name] = normalized

    for old, new in rename_map.items():
        updated_code = re.sub(r"\b" + re.escape(old) + r"\b", new, updated_code)

    print(f"   已规范化: {len(rename_map)} 个变量名")

    print("\n" + "=" * 80)
    print("[ImageDownloadNode] 图片处理完成")
    print(f"   总计: {len(image_urls)}，已上传: {len(successful_uploads)}，失败: {len(failed)}")
    print("=" * 80 + "\n")

    return {"figmaCode": updated_code}
