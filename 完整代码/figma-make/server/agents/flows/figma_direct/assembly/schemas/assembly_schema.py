"""
Figma 直连 - 组装阶段类型定义。
"""
from typing import Dict, Optional

from pydantic import BaseModel, Field


class AssemblyStats(BaseModel):
    totalFiles: int
    categories: Dict[str, int]


class FigmaAssemblyResult(BaseModel):
    files: Dict[str, str] = Field(
        description="Sandpack 文件映射：键为文件路径，值为文件内容"
    )
    stats: Optional[AssemblyStats] = None
