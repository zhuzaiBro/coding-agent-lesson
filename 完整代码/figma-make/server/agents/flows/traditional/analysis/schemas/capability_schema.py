"""step2: Capability analysis schema."""
from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class PageType(str, Enum):
    landing = "landing"
    dashboard = "dashboard"
    list = "list"
    detail = "detail"
    form = "form"
    workspace = "workspace"
    settings = "settings"
    profile = "profile"
    other = "other"


class DataComplexity(str, Enum):
    simple = "simple"
    static = "static"
    list_detail = "list+detail"
    complex = "complex"


class Page(BaseModel):
    pageType: PageType = Field(description="Page type")
    pageId: str = Field(description="Unique page identifier (PascalCase)")
    description: str = Field(description="Page functionality description")
    supportedGoals: List[str] = Field(description="Business goals this page supports")


class Behavior(BaseModel):
    behaviorId: str = Field(description="Behavior identifier (camelCase)")
    description: str = Field(description="Behavior description")
    scope: List[str] = Field(description="List of page IDs involved")
    optional: bool = Field(description="Whether this is an optional feature")


class DataModel(BaseModel):
    modelId: str = Field(description="Unique model identifier (PascalCase)")
    description: str = Field(description="Model purpose description")
    complexity: DataComplexity = Field(description="Data complexity")
    fields: List[str] = Field(description="List of fields")


class CapabilityResult(BaseModel):
    pages: List[Page] = Field(description="List of pages in the application")
    behaviors: List[Behavior] = Field(description="List of interaction behaviors")
    dataModels: List[DataModel] = Field(description="Data models required by the application")
