"""step10: Service layer files generation schema."""
from typing import List

from pydantic import BaseModel, Field


class ServiceFile(BaseModel):
    path: str = Field(description="Service/logic file path, typically in /services/ directory")
    content: str = Field(
        description="Complete file code. Should include data access functions and business logic based on mock data. Must import mock data and types correctly."
    )
    description: str = Field(description="Description of this service file's functionality")


class ServiceResult(BaseModel):
    files: List[ServiceFile] = Field(description="List of generated service/logic files")
