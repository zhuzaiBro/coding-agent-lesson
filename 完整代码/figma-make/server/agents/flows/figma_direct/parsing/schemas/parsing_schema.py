"""
Figma Direct - Parsing phase type definitions.

Covers Step 1 (AST Parser) -> Step 2 (Block Extract) -> Step 3 (Geometry Group)
"""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== Step 1: AST Parser ====================

class SourceLoc(BaseModel):
    startLine: int
    endLine: int


class JsxElement(BaseModel):
    index: int = Field(description="Order in parent node")
    rawJsx: str = Field(description="Raw JSX code snippet")
    className: Optional[str] = Field(default=None, description="className attribute value")
    inlineStyle: Optional[str] = Field(default=None, description="Inline style object (raw string)")
    nodeId: Optional[str] = Field(default=None, description="data-node-id attribute value")
    dataName: Optional[str] = Field(default=None, description="data-name attribute value")
    childrenCount: int = Field(description="Number of direct child elements")
    loc: SourceLoc = Field(description="Source location")


class GlobalAsset(BaseModel):
    variableName: str = Field(description="Variable name (e.g. imgRectangle53)")
    url: str = Field(description="Image URL")


class HelperComponent(BaseModel):
    name: str = Field(description="Component name")
    rawCode: str = Field(description="Complete code")
    loc: SourceLoc = Field(description="Source location")


class AstParserOutput(BaseModel):
    entryComponentName: str = Field(description="Main entry component name (export default)")
    jsxElements: List[JsxElement] = Field(description="Top-level JSX element list")
    globalAssets: List[GlobalAsset] = Field(description="Global image assets")
    helperComponents: List[HelperComponent] = Field(description="Helper components")


# ==================== Step 2: Block Extract ====================

class LayoutBlock(BaseModel):
    index: int = Field(description="Index in original list")
    rawJsx: str = Field(description="Raw JSX code snippet")
    top: float = Field(description="Y-axis position (px)")
    left: float = Field(description="X-axis position (px)")
    width: float = Field(description="Width (px), 0 if unspecified")
    height: float = Field(description="Height (px), 0 if unspecified")
    texts: List[str] = Field(description="All text content")
    usedAssets: List[str] = Field(description="Referenced image variable names")
    childrenCount: int = Field(description="Number of direct child elements")
    isBackground: bool = Field(description="Whether this is a full-page background element")
    nodeId: Optional[str] = Field(default=None)
    dataName: Optional[str] = Field(default=None)


class BlockExtractOutput(BaseModel):
    layoutBlocks: List[LayoutBlock] = Field(description="Normalized layout block list")
    pageHeight: float = Field(description="Estimated total page height (px)")


# ==================== Step 3: Geometry Group ====================

class TopRange(BaseModel):
    min: float
    max: float


class Section(BaseModel):
    index: int = Field(description="Section number (0-based)")
    blocks: List[LayoutBlock] = Field(description="Layout blocks in this section")
    topRange: TopRange = Field(description="Y-axis range")
    allTexts: List[str] = Field(description="Aggregated text content")
    allAssets: List[str] = Field(description="Aggregated image variable references")
    totalBlocks: int = Field(description="Total number of layout blocks")
    backgroundBlocks: List[LayoutBlock] = Field(description="Background elements in this section")


class GeometryGroupOutput(BaseModel):
    sections: List[Section] = Field(description="List of grouped sections")
    threshold: float = Field(description="Grouping threshold (px)")
