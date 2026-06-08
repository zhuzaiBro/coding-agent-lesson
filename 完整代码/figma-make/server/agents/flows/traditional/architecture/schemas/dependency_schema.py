"""step6: Dependency management schema."""
from typing import Dict

from pydantic import BaseModel, Field


class DependencyResult(BaseModel):
    dependencies: Dict[str, str] = Field(
        description="Required additional NPM dependencies. Key is package name, value is version number."
    )
    reason: str = Field(description="Brief reason for choosing these dependencies based on component needs")
