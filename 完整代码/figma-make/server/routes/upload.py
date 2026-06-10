"""
用户参考图上传 API。

接收 multipart 图片 → 校验类型与大小 → 上传阿里云 OSS → 返回公网 URL。
聊天附件与 Figma 流程中的图片替换均依赖此接口。
"""
import os
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from utils.oss import get_oss_client
from config.oss import oss_config

router = APIRouter()

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/image")
async def upload_image(file: UploadFile = File(...)):
    print("\n[Upload API] Received POST request")
    print(f"[Upload] Original filename: {file.filename}")
    print(f"[Upload] Content type: {file.content_type}")

    # Validate extension
    if file.filename:
        ext = Path(file.filename).suffix.lower()
    else:
        ext = ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Only image files are allowed.",
        )

    # Read file content
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB.",
        )

    print(f"[Upload] File size: {len(content) / 1024:.2f} KB")

    # Get OSS client
    try:
        client = get_oss_client()
    except Exception as err:
        print(f"[Upload] OSS client initialization failed: {err}")
        raise HTTPException(status_code=500, detail="OSS not configured")

    print("[Upload] OSS client ready")

    # Generate filename
    date_str = datetime.now().strftime("%Y%m%d")
    file_uuid = str(uuid.uuid4())
    filename = f"images/{date_str}-{file_uuid}{ext}"

    # Upload to OSS
    try:
        import io
        result = client.put_object(filename, io.BytesIO(content))

        # Build URL
        protocol = "https" if oss_config.secure else "http"
        file_url = f"{protocol}://{oss_config.bucket}.{oss_config.endpoint}/{filename}"

        print(f"[Upload] Upload successful: {file_url}")

        return {
            "url": file_url,
            "name": file.filename or filename,
        }
    except Exception as error:
        print(f"[Upload] Upload failed: {error}")
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(error)}",
        )
