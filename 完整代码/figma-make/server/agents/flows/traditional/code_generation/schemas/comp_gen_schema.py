"""step12: Component generation schema."""
from typing import Optional

from pydantic import BaseModel, Field


class CompGenResult(BaseModel):
    path: str = Field(description="Component file path, must end in .tsx")
    content: str = Field(
        description="Complete React component code. Must include all necessary imports, use Tailwind CSS for styling."
    )
    description: Optional[str] = Field(default=None, description="Brief description of the component's functionality")
