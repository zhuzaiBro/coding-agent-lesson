"""step5: Project structure schema."""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class FileKind(str, Enum):
    template = "template"
    overwrite = "overwrite"
    new = "new"


class FileNode(BaseModel):
    path: str = Field(description="File absolute path, must start with /")
    kind: FileKind = Field(description="File processing strategy: template/overwrite/new")
    description: str = Field(description="Brief file purpose description")
    sourceCorrelation: Optional[str] = Field(
        default=None,
        description="Source correlation: for 'new' files, link to ComponentID or ModelName. Null for template/non-generated files.",
    )
    generatedBy: str = Field(
        description="Step identifier responsible for generating content (e.g. 'step6-types', 'step7-mock')"
    )


class StructureResult(BaseModel):
    files: List[FileNode] = Field(description="Complete file list required for the Sandpack project")
