"""
Figma 直连 - 解析阶段类型定义。

覆盖 Step 1（AST 解析）→ Step 2（布局块提取）→ Step 3（几何分组）
"""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== Step 1: AST 解析 ====================

class SourceLoc(BaseModel):
    startLine: int
    endLine: int


class JsxElement(BaseModel):
    index: int = Field(description="在父节点中的顺序")
    rawJsx: str = Field(description="原始 JSX 代码片段")
    className: Optional[str] = Field(default=None, description="className 属性值")
    inlineStyle: Optional[str] = Field(default=None, description="内联 style 对象（原始字符串）")
    nodeId: Optional[str] = Field(default=None, description="data-node-id 属性值")
    dataName: Optional[str] = Field(default=None, description="data-name 属性值")
    childrenCount: int = Field(description="直接子元素数量")
    loc: SourceLoc = Field(description="源码位置")


class GlobalAsset(BaseModel):
    variableName: str = Field(description="变量名（如 imgRectangle53）")
    url: str = Field(description="图片 URL")


class HelperComponent(BaseModel):
    name: str = Field(description="组件名")
    rawCode: str = Field(description="完整代码")
    loc: SourceLoc = Field(description="源码位置")


class AstParserOutput(BaseModel):
    entryComponentName: str = Field(description="主入口组件名（export default）")
    jsxElements: List[JsxElement] = Field(description="顶层 JSX 元素列表")
    globalAssets: List[GlobalAsset] = Field(description="全局图片资源")
    helperComponents: List[HelperComponent] = Field(description="辅助组件")


# ==================== Step 2: 布局块提取 ====================

class LayoutBlock(BaseModel):
    index: int = Field(description="在原始列表中的索引")
    rawJsx: str = Field(description="原始 JSX 代码片段")
    top: float = Field(description="Y 轴位置（px）")
    left: float = Field(description="X 轴位置（px）")
    width: float = Field(description="宽度（px），未指定时为 0")
    height: float = Field(description="高度（px），未指定时为 0")
    texts: List[str] = Field(description="全部文本内容")
    usedAssets: List[str] = Field(description="引用的图片变量名")
    childrenCount: int = Field(description="直接子元素数量")
    isBackground: bool = Field(description="是否为整页背景元素")
    nodeId: Optional[str] = Field(default=None)
    dataName: Optional[str] = Field(default=None)


class BlockExtractOutput(BaseModel):
    layoutBlocks: List[LayoutBlock] = Field(description="规范化布局块列表")
    pageHeight: float = Field(description="估算的页面总高度（px）")


# ==================== Step 3: 几何分组 ====================

class TopRange(BaseModel):
    min: float
    max: float


class Section(BaseModel):
    index: int = Field(description="Section 序号（从 0 开始）")
    blocks: List[LayoutBlock] = Field(description="该 Section 内的布局块")
    topRange: TopRange = Field(description="Y 轴范围")
    allTexts: List[str] = Field(description="聚合文本内容")
    allAssets: List[str] = Field(description="聚合图片变量引用")
    totalBlocks: int = Field(description="布局块总数")
    backgroundBlocks: List[LayoutBlock] = Field(description="该 Section 内的背景元素")


class GeometryGroupOutput(BaseModel):
    sections: List[Section] = Field(description="分组后的 Section 列表")
    threshold: float = Field(description="分组阈值（px）")
