"""
Figma 直连 - 重构阶段类型定义。

覆盖 Step 4（Section 命名 - AI）→ Step 5（组件生成 - AI）
"""
from typing import List

from pydantic import BaseModel, Field


# ==================== Step 4: Section 命名 ====================

class NamedSection(BaseModel):
    index: int = Field(description="Section 序号（对应 geometryGroup 结果中的 index）")
    componentName: str = Field(description="PascalCase 组件名，如 HeroSection、FeatureGrid")
    description: str = Field(description="该 Section 的语义描述")
    fileName: str = Field(description="建议文件名（不含扩展名）")


class SectionNamingOutput(BaseModel):
    namedSections: List[NamedSection] = Field(description="所有 Section 的命名结果")


# ==================== Step 5: 组件生成 ====================

class GeneratedFile(BaseModel):
    filePath: str = Field(description="文件路径，如 components/HeroSection.tsx")
    code: str = Field(description="完整 React 组件代码（含 import 与 export）")
    componentName: str = Field(description="组件名")


class ComponentGenResult(BaseModel):
    sectionIndex: int = Field(description="Section 序号")
    file: GeneratedFile = Field(description="生成的组件文件")
