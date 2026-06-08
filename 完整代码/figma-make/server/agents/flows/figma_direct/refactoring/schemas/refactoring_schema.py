"""
Figma Direct - Refactoring phase type definitions.

Covers Step 4 (Section Naming - AI) -> Step 5 (Component Gen - AI)
"""
from typing import List

from pydantic import BaseModel, Field


# ==================== Step 4: Section Naming ====================

class NamedSection(BaseModel):
    index: int = Field(description="Section number (corresponds to geometryGroup result index)")
    componentName: str = Field(description="Component name in PascalCase, e.g. HeroSection, FeatureGrid")
    description: str = Field(description="Semantic description of this section")
    fileName: str = Field(description="Suggested file name without extension")


class SectionNamingOutput(BaseModel):
    namedSections: List[NamedSection] = Field(description="Naming results for all sections")


# ==================== Step 5: Component Gen ====================

class GeneratedFile(BaseModel):
    filePath: str = Field(description="File path, e.g. components/HeroSection.tsx")
    code: str = Field(description="Complete React component code including imports and exports")
    componentName: str = Field(description="Component name")


class ComponentGenResult(BaseModel):
    sectionIndex: int = Field(description="Section number")
    file: GeneratedFile = Field(description="Generated component file")
