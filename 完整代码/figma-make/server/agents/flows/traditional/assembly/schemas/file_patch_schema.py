"""Structured output for LLM file patches (debug fix & user modify)."""
from typing import List

from pydantic import BaseModel, Field


class FilePatch(BaseModel):
    path: str = Field(description="Sandpack path, e.g. /pages/TodoList.tsx")
    content: str = Field(description="Full updated file content")
    reason: str = Field(default="", description="One-line reason for this change")


class FilePatchResult(BaseModel):
    patches: List[FilePatch] = Field(
        description="Files to update; only include paths you actually changed"
    )
    summary: str = Field(description="Brief summary of changes")
