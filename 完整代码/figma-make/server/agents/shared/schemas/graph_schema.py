"""
主图 LangGraph 状态 Schema。

使用 TypedDict + Annotated 以支持 reducer 合并（如并行节点 fan-in）。
"""
import operator
from typing import Annotated, Any, Dict, List, Optional

from typing_extensions import TypedDict


class GraphState(TypedDict, total=False):
    """
    主图状态定义。

    带 Annotated[list, operator.add] 的字段支持 fan-in（并行节点结果合并）。
    """
    # 初始输入：对话历史
    messages: List[Any]

    # 初始输入：各节点 Mock 配置
    mockConfig: Optional[Dict[str, bool]]

    # 文本提示（遗留字段）
    textPrompt: Optional[str]

    # Figma URL（figma 流程）
    figmaUrl: Optional[str]

    # step0: 行为分析
    analysis: Optional[Dict[str, Any]]

    # step0.5: 控制流标志
    skipGeneration: Optional[bool]

    # step1: 意图详情
    intent: Optional[Dict[str, Any]]

    # step2: 能力分析
    capabilities: Optional[Dict[str, Any]]

    # step3: UI 架构
    ui: Optional[Dict[str, Any]]

    # step4: 组件契约
    components: Optional[Dict[str, Any]]

    # step5: 项目结构
    structure: Optional[Dict[str, Any]]

    # step6: 依赖管理
    dependency: Optional[Dict[str, Any]]

    # step7: 类型定义
    types: Optional[Dict[str, Any]]

    # step8: 工具函数文件
    utils: Optional[Dict[str, Any]]

    # step9: Mock 数据
    mockData: Optional[Dict[str, Any]]

    # step10: 服务层文件
    service: Optional[Dict[str, Any]]

    # step11: Hooks 层文件
    hooks: Optional[Dict[str, Any]]

    # step11.5: 生成的模块/导出/导入 DSL
    projectManifest: Optional[Dict[str, Any]]
    projectManifestText: Optional[str]

    # step12: UI 组件代码（组件子图 fan-in）
    componentsCode: Annotated[List[Dict[str, Any]], operator.add]

    # step13: 页面代码（页面子图 fan-in）
    pagesCode: Annotated[List[Dict[str, Any]], operator.add]

    # step14: Layout 节点输出
    layouts: Optional[Dict[str, Any]]

    # step15: 全局样式
    styles: Optional[Dict[str, Any]]

    # step15: App.tsx 入口
    app: Optional[Dict[str, Any]]

    # step16: 组装后的文件（Sandpack 格式）
    files: Optional[Dict[str, Any]]

    # --- Figma 流程专用 ---
    # MCP 返回的原始 Figma 代码
    figmaCode: Optional[str]

    # 已下载图片映射：{url: bytes}
    downloadedImages: Optional[Dict[str, bytes]]

    # AST 解析块
    parsedBlocks: Optional[List[Dict[str, Any]]]

    # 布局块提取结果（坐标、文本、资源）
    blockExtracts: Optional[List[Dict[str, Any]]]

    # 几何分组结果
    geometryGroups: Optional[List[Dict[str, Any]]]

    # 已命名 Section
    namedSections: Optional[List[Dict[str, Any]]]

    # 生成的 Figma 组件代码
    figmaComponents: Optional[List[Dict[str, Any]]]
