"""
Figma Direct - Assembly phase type definitions.
"""
from typing import Dict, Optional

from pydantic import BaseModel, Field


class AssemblyStats(BaseModel):
    totalFiles: int
    categories: Dict[str, int]


class FigmaAssemblyResult(BaseModel):
    files: Dict[str, str] = Field(
        description="Sandpack file mapping: key is file path, value is file content"
    )
    stats: Optional[AssemblyStats] = None
