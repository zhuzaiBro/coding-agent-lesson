"""step15: App.tsx generation schema."""
from pydantic import BaseModel, Field


class AppGenResult(BaseModel):
    path: str = Field(description="File path, fixed as /App.tsx")
    content: str = Field(
        description="Complete App.tsx code including route configuration, Provider wrapping and component imports"
    )
    description: str = Field(description="Brief description of route structure and Providers used")
