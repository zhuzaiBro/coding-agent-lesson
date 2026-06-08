"""step1: Intent analysis schema."""
from typing import List, Optional

from pydantic import BaseModel, Field


class Product(BaseModel):
    name: str = Field(description="Application name")
    description: str = Field(description="Application description")
    targetUsers: List[str] = Field(description="Target users")
    primaryScenario: str = Field(description="Primary usage scenario")


class Goals(BaseModel):
    primary: List[str] = Field(description="Primary goals of the application")
    secondary: Optional[List[str]] = Field(default=None, description="Secondary goals")


class IntentResult(BaseModel):
    product: Product
    goals: Goals
    nonGoals: List[str] = Field(description="Goals the application does NOT need to achieve")
    assumptions: Optional[List[str]] = Field(default=None, description="Design assumptions")
    category: str = Field(description="Application category/type")
