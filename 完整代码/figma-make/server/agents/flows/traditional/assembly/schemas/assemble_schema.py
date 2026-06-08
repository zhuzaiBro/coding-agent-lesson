"""step16: File assembly schema."""
from typing import Dict, Optional

from pydantic import BaseModel, Field


class AssembleStats(BaseModel):
    totalFiles: int = Field(description="Total number of files")
    categories: Dict[str, int] = Field(description="File count per category")


class AssembleResult(BaseModel):
    files: Dict[str, str] = Field(
        description="Sandpack file mapping: key is file path, value is file content"
    )
    stats: Optional[AssembleStats] = None
