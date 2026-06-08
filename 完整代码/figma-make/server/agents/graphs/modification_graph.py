"""
用户修改流程图（在已生成应用上迭代）

loadExistingNode → userModifyNode → postProcessNode → compileCheckNode ⇄ debugFixNode → END

与完整 Traditional 19 节点分离：只加载现有文件、按用户描述打补丁、再走 AST/编译/自动修编译错误。
"""
from typing import Any, Dict, List, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from agents.flows.traditional.assembly.nodes.compile_check_node import compile_check_node
from agents.flows.traditional.assembly.nodes.compile_fix_router import (
    route_after_compile_check,
)
from agents.flows.traditional.assembly.nodes.debug_fix_node import debug_fix_node
from agents.flows.traditional.assembly.nodes.load_existing_node import load_existing_node
from agents.flows.traditional.assembly.nodes.post_process_node import post_process_node
from agents.flows.traditional.assembly.nodes.user_modify_node import user_modify_node

checkpointer = MemorySaver()


class ModificationGraphState(TypedDict, total=False):
    messages: List[Any]
    mockConfig: Optional[Dict[str, Any]]
    existingFiles: Optional[Dict[str, str]]
    modificationRequest: Optional[str]
    modification: Optional[Dict[str, Any]]
    projectManifestText: Optional[str]
    files: Optional[Dict[str, Any]]


def build_modification_agent():
    graph = StateGraph(ModificationGraphState)

    graph.add_node("loadExistingNode", load_existing_node)
    graph.add_node("userModifyNode", user_modify_node)
    graph.add_node("postProcessNode", post_process_node)
    graph.add_node("compileCheckNode", compile_check_node)
    graph.add_node("debugFixNode", debug_fix_node)

    graph.add_edge(START, "loadExistingNode")
    graph.add_edge("loadExistingNode", "userModifyNode")
    graph.add_edge("userModifyNode", "postProcessNode")
    graph.add_edge("postProcessNode", "compileCheckNode")
    graph.add_conditional_edges(
        "compileCheckNode",
        route_after_compile_check,
        {"debugFixNode": "debugFixNode", END: END},
    )
    graph.add_edge("debugFixNode", "compileCheckNode")

    return graph.compile(checkpointer=checkpointer)
