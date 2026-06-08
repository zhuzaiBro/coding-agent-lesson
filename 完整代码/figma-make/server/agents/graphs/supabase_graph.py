"""
Supabase 数据库上下文子图（foundation 阶段）

串行 MCP 流水线，在 typeNode 之前拉取真实库表结构，供 serviceNode / hooksNode 注入提示词：

connectNode → fetchConfigNode → fetchSchemaNode → fetchTypesNode → assembleNode → END

由 traditional_graph 的 supabaseSubgraph bridge 节点调用（与 componentSubgraph / pageSubgraph 同模式）。
"""
from typing import Any, Dict, List, Optional

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from agents.flows.traditional.architecture.nodes.supabase_assemble_node import (
    supabase_assemble_node,
)
from agents.flows.traditional.architecture.nodes.supabase_connect_node import (
    supabase_connect_node,
)
from agents.flows.traditional.architecture.nodes.supabase_fetch_config_node import (
    supabase_fetch_config_node,
)
from agents.flows.traditional.architecture.nodes.supabase_fetch_schema_node import (
    supabase_fetch_schema_node,
)
from agents.flows.traditional.architecture.nodes.supabase_fetch_types_node import (
    supabase_fetch_types_node,
)


class SupabaseSubgraphState(TypedDict, total=False):
    """Supabase subgraph state."""
    useSupabase: Optional[bool]
    messages: List[Any]
    connected: bool
    error: Optional[str]
    projectUrl: str
    publishableKeyHint: bool
    schemaSummary: str
    typescriptTypes: str
    supabase: Dict[str, Any]


def build_supabase_graph():
    """Build and compile the Supabase MCP subgraph."""
    graph = StateGraph(SupabaseSubgraphState)

    graph.add_node("connectNode", supabase_connect_node)
    graph.add_node("fetchConfigNode", supabase_fetch_config_node)
    graph.add_node("fetchSchemaNode", supabase_fetch_schema_node)
    graph.add_node("fetchTypesNode", supabase_fetch_types_node)
    graph.add_node("assembleNode", supabase_assemble_node)

    graph.add_edge(START, "connectNode")
    graph.add_edge("connectNode", "fetchConfigNode")
    graph.add_edge("fetchConfigNode", "fetchSchemaNode")
    graph.add_edge("fetchSchemaNode", "fetchTypesNode")
    graph.add_edge("fetchTypesNode", "assembleNode")
    graph.add_edge("assembleNode", END)

    return graph.compile()


supabase_graph = build_supabase_graph()
