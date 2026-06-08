"""step9: Mock data generation schema."""
from typing import List

from pydantic import BaseModel, Field


class MockDataFile(BaseModel):
    path: str = Field(description="File path, typically in /data/ directory, e.g. '/data/novels.ts'")
    content: str = Field(
        description="Complete file code. Contains TypeScript interfaces (export interface) and mock data constants (export const). No helper functions."
    )
    description: str = Field(description="Brief description of this data file's purpose")


class MockDataResult(BaseModel):
    files: List[MockDataFile] = Field(description="List of generated mock data files")
