"""step14.5: Layout component generation schema."""
from typing import Dict, List

from pydantic import BaseModel, Field


class LayoutGen(BaseModel):
    path: str = Field(description="Layout component file path, must end in .tsx")
    content: str = Field(description="Complete React code for the Layout component. Must include Outlet for sub-routes, use Tailwind CSS.")
    description: str = Field(description="Brief description of this Layout and which pages use it")
    pages: List[str] = Field(description="List of pages using this Layout")


class LayoutNodeOutput(BaseModel):
    layoutsCode: List[LayoutGen] = Field(description="Array of all generated Layout component code")
    routeStructure: Dict[str, List[str]] = Field(
        description="Route nesting structure map: key is Layout name, value is array of page names under that Layout"
    )
