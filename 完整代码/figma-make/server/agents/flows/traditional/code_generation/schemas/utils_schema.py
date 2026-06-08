"""step8: Utility function files generation schema."""
from typing import List, Optional

from pydantic import BaseModel, Field


class UtilsFile(BaseModel):
    path: str = Field(description="File path, typically /lib/utils.ts")
    code: str = Field(description="Complete TypeScript code content")
    description: Optional[str] = Field(default=None, description="Brief description of utility functions")


class UtilsGenerationResult(BaseModel):
    files: List[UtilsFile] = Field(description="List of generated utility files")
