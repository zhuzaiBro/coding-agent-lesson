"""step13: Page generation schema."""
from pydantic import BaseModel, Field


class PageGenResult(BaseModel):
    path: str = Field(description="Page file path (e.g. /pages/Dashboard.tsx)")
    content: str = Field(description="Complete React page code")
    description: str = Field(description="Brief description of this page")
