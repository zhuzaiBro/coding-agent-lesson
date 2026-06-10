"""
主图工厂（按模式返回已编译的 LangGraph）。

routes/chat.py 在路由适配器判定 flow 后，选择对应 Agent 执行：
- "traditional"   → traditional_graph.py（19 节点从零生成）
- "figma"         → figma_graph.py（MCP 拉设计稿再拆解）
- "modification"  → modification_graph.py（在已有 Sandpack 文件上打补丁）

模块在 import 时不会执行生成，仅提供 build_agent(mode) 工厂函数。
"""
from typing import Literal

from agents.graphs.traditional_graph import build_traditional_agent
from agents.graphs.figma_graph import build_figma_agent
from agents.graphs.modification_graph import build_modification_agent
from agents.shared.utils.figma_url import extract_figma_url

__all__ = ["build_agent", "extract_figma_url"]


def build_agent(mode: Literal["traditional", "figma", "modification"] = "traditional"):
    """编译并返回指定模式的 LangGraph（带 MemorySaver 的已在各 build_*_agent 内配置）。"""
    if mode == "figma":
        print("[MainGraph] Building Figma direct graph")
        return build_figma_agent()

    if mode == "modification":
        print("[MainGraph] Building Modification graph")
        return build_modification_agent()

    print("[MainGraph] Building Traditional graph")
    return build_traditional_agent()
