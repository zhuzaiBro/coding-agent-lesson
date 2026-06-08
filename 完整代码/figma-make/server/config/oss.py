import os
from dataclasses import dataclass


@dataclass
class OSSConfig:
    access_key_id: str
    access_key_secret: str
    endpoint: str
    bucket: str
    region: str = ""
    secure: bool = True


oss_config = OSSConfig(
    access_key_id=os.getenv("ALI_OSS_AK", ""),
    access_key_secret=os.getenv("ALI_OSS_SK", ""),
    endpoint=os.getenv("ALI_OSS_ENDPOINT", "oss-cn-hangzhou.aliyuncs.com"),
    bucket=os.getenv("ALI_OSS_BUCKET", ""),
    secure=True,
)
