"""step14: Global styles generation schema."""
from pydantic import BaseModel, Field


class StyleGenResult(BaseModel):
    path: str = Field(description="Style file path, fixed as styles.css")
    content: str = Field(
        description="Complete CSS code. Should include CSS variable definitions, layout container classes, animation effects. Complementary to Tailwind, avoid duplication."
    )
    description: str = Field(description="Brief description of main style rules in this file")
