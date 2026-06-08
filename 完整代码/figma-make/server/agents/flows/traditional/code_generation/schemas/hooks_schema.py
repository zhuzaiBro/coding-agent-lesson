"""step11: Hooks generation schema."""
from typing import List

from pydantic import BaseModel, Field


class HookFile(BaseModel):
    path: str = Field(description="Hook file path, typically in /hooks/ directory, e.g. '/hooks/useNovels.ts'")
    content: str = Field(
        description="Complete file code. Should include custom hook logic based on Service layer, handling data loading, loading states and errors."
    )
    description: str = Field(description="Description of this hook file's functionality")


class HooksResult(BaseModel):
    files: List[HookFile] = Field(description="List of generated custom hook files")
