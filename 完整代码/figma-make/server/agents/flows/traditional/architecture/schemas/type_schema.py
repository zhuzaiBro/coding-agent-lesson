"""step7: Business data type definitions schema."""
from typing import List

from pydantic import BaseModel, Field


class TypeFile(BaseModel):
    path: str = Field(description="File path, e.g. /types/Novel.ts")
    code: str = Field(description="Type definition code content (interface/type)")
    modelId: str = Field(description="Corresponding data model ID")


class TypeGenerationResult(BaseModel):
    files: List[TypeFile] = Field(description="List of generated type definition files")
