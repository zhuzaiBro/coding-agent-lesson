"""
传统生成流程图（prompt 驱动）

完整 19 节点串行流水线，每个节点完成后推送 SSE 事件到前端：

【规划阶段】analysisNode → (路由) intentNode → ...  |  QA+DB: supabaseSubgraph → inquiryNode → chatReplyNode
【架构阶段】→ structureNode → dependencyNode → supabaseSubgraph → typeNode
【代码生成】→ utilsNode → mockDataNode → serviceNode → hooksNode
【并行生成】→ componentSubgraph（所有组件并行）→ pageSubgraph（所有页面并行）
【组装阶段】→ layoutNode → styleGenNode → appGenNode → assembleNode → postProcessNode
            → compileCheckNode ⇄ debugFixNode（编译失败时 LLM 修复，可配置重试）→ END

设计要点：
- 使用 MemorySaver 实现会话级状态持久化，同一 thread_id 支持多轮修改
- supabaseSubgraph 在 foundation 阶段串行拉取 MCP 表结构（connect → config → schema → types）
- componentSubgraph / pageSubgraph 是 fan-out 子图，内部对每个文件并发生成
- bridge 节点（run_supabase_graph / run_component_graph / run_page_graph）负责主图与子图之间的数据桥接
"""
import operator
from typing import Annotated, Any, Dict, List, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

# Input Processing Phase
from agents.flows.traditional.input_processing.nodes.intent_node import intent_node

# Analysis Phase
from agents.flows.traditional.analysis.nodes.analysis_node import analysis_node
from agents.flows.traditional.analysis.nodes.analysis_router import route_after_analysis
from agents.flows.traditional.inquiry.nodes.chat_reply_node import chat_reply_node
from agents.flows.traditional.inquiry.nodes.database_inquiry_node import database_inquiry_node
from agents.flows.traditional.analysis.nodes.capability_node import capability_node
from agents.flows.traditional.analysis.nodes.ui_node import ui_node
from agents.flows.traditional.analysis.nodes.component_node import component_node

# Architecture Phase
from agents.flows.traditional.architecture.nodes.structure_node import structure_node
from agents.flows.traditional.architecture.nodes.dependency_node import dependency_node
from agents.utils.supabase_integration import needs_database_connection
from agents.flows.traditional.architecture.nodes.type_node import type_node
from agents.flows.traditional.architecture.nodes.layout_node import layout_node
from agents.flows.traditional.architecture.nodes.manifest_node import manifest_node

# Code Generation Phase
from agents.flows.traditional.code_generation.nodes.utils_node import utils_node
from agents.flows.traditional.code_generation.nodes.mock_data_node import mock_data_node
from agents.flows.traditional.code_generation.nodes.service_node import service_node
from agents.flows.traditional.code_generation.nodes.hooks_node import hooks_node
from agents.flows.traditional.code_generation.nodes.style_gen_node import style_gen_node

# Assembly Phase
from agents.flows.traditional.assembly.nodes.app_gen_node import app_gen_node
from agents.flows.traditional.assembly.nodes.assemble_node import assemble_node
from agents.flows.traditional.assembly.nodes.post_process_node import post_process_node
from agents.flows.traditional.assembly.nodes.compile_check_node import compile_check_node
from agents.flows.traditional.assembly.nodes.compile_fix_router import (
    route_after_compile_check,
)
from agents.flows.traditional.assembly.nodes.debug_fix_node import debug_fix_node

# Subgraphs
from agents.graphs.component_graph import component_graph
from agents.graphs.page_graph import page_graph
from agents.graphs.supabase_graph import supabase_graph

# Mock utilities
from agents.utils.mock import try_execute_mock

checkpointer = MemorySaver()


class TraditionalGraphState(TypedDict, total=False):
    """传统流程 LangGraph 状态：各节点读写约定字段，由 MemorySaver 按 thread_id 持久化。"""
    messages: List[Any]
    mockConfig: Optional[Dict[str, Any]]
    textPrompt: Optional[str]
    analysis: Optional[Dict[str, Any]]
    skipGeneration: Optional[bool]
    intent: Optional[Dict[str, Any]]
    capabilities: Optional[Dict[str, Any]]
    ui: Optional[Dict[str, Any]]
    components: Optional[Dict[str, Any]]
    structure: Optional[Dict[str, Any]]
    dependency: Optional[Dict[str, Any]]
    types: Optional[Dict[str, Any]]
    utils: Optional[Dict[str, Any]]
    mockData: Optional[Dict[str, Any]]
    service: Optional[Dict[str, Any]]
    hooks: Optional[Dict[str, Any]]
    projectManifest: Optional[Dict[str, Any]]
    projectManifestText: Optional[str]
    useSupabase: Optional[bool]
    supabase: Optional[Dict[str, Any]]
    inquiry: Optional[Dict[str, Any]]
    chatReply: Optional[Dict[str, Any]]
    # Fan-in: these accumulate via operator.add in subgraphs,
    # but in the main graph they're overwritten as a whole result.
    componentsCode: Optional[List[Dict[str, Any]]]
    pagesCode: Optional[List[Dict[str, Any]]]
    layouts: Optional[Dict[str, Any]]
    styles: Optional[Dict[str, Any]]
    app: Optional[Dict[str, Any]]
    files: Optional[Dict[str, Any]]


# --- 子图桥接节点 ---
# 主图与子图状态字段不完全一致：bridge 负责抽取输入、调用子图、把输出写回主图 state。

async def run_supabase_graph(state: dict) -> dict:
    """桥接 Supabase 子图：拉取 projectUrl / schema / TS types，写入 state.supabase。"""
    if not needs_database_connection(state):
        print("[MainGraph] Supabase subgraph skipped (LLM/user did not require database)")
        return {}

    mock_result = await try_execute_mock(
        state,
        "supabaseSubgraph",
        "supabaseResult.json",
        lambda data, _state: {"supabase": data.get("supabase") or data},
    )
    if mock_result:
        return mock_result

    print("[MainGraph] Invoking Supabase Subgraph...")
    result = await supabase_graph.ainvoke({
        "useSupabase": state.get("useSupabase"),
        "messages": state.get("messages"),
    })
    return {"supabase": result.get("supabase", {})}


async def run_component_graph(state: dict) -> dict:
    """桥接组件子图：从 structure.files 筛出 /components/*.tsx 并 fan-out 并行生成。"""
    # Mock mode check
    mock_result = await try_execute_mock(
        state,
        "componentSubgraph",
        "compGenResult.json",
        lambda data, _state: {"componentsCode": data.get("componentsCode") or data},
    )
    if mock_result:
        return mock_result

    all_files = (state.get("structure") or {}).get("files", [])
    components_to_generate = [
        f for f in all_files
        if "/components/" in f.get("path", "")
        and (f.get("path", "").endswith(".tsx") or f.get("path", "").endswith(".jsx"))
    ]

    print(f"[MainGraph] Invoking Component Subgraph for {len(components_to_generate)} items...")

    subgraph_input = {
        "componentsToGenerate": components_to_generate,
        "context": {
            "hooks": state.get("hooks"),
            "types": state.get("types"),
            "service": state.get("service"),
            "components": state.get("components"),
            "projectManifestText": state.get("projectManifestText"),
        },
    }

    result = await component_graph.ainvoke(subgraph_input)

    return {
        "componentsCode": result.get("componentsCode", []),
    }


async def run_page_graph(state: dict) -> dict:
    """桥接页面子图：从 structure.files 筛出 /pages/*.tsx，可引用已生成的 componentsCode。"""
    # Mock mode check
    mock_result = await try_execute_mock(
        state,
        "pageSubgraph",
        "pageGenResult.json",
        lambda data, _state: {
            "pagesCode": data if isinstance(data, list) else data.get("pagesCode") or data
        },
    )
    if mock_result:
        return mock_result

    all_files = (state.get("structure") or {}).get("files", [])
    pages_to_generate = [
        f for f in all_files
        if "/pages/" in f.get("path", "")
        and (f.get("path", "").endswith(".tsx") or f.get("path", "").endswith(".jsx"))
    ]

    print(f"[MainGraph] Invoking Page Subgraph for {len(pages_to_generate)} items...")

    subgraph_input = {
        "pagesToGenerate": pages_to_generate,
        "context": {
            "hooks": state.get("hooks"),
            "componentResult": state.get("componentsCode") or [],
            "types": state.get("types"),
            "projectManifestText": state.get("projectManifestText"),
        },
    }

    result = await page_graph.ainvoke(subgraph_input)

    return {
        "pagesCode": result.get("pagesCode", []),
    }


def build_traditional_agent():
    """编译传统 19 节点图；analysis 后三路分支，compileCheck 失败可循环 debugFix。"""
    graph = StateGraph(TraditionalGraphState)

    # Step 0: Analysis + inquiry branch
    graph.add_node("analysisNode", analysis_node)
    graph.add_node("inquiryNode", database_inquiry_node)
    graph.add_node("chatReplyNode", chat_reply_node)

    # Step 1-11: Core planning nodes
    graph.add_node("intentNode", intent_node)
    graph.add_node("capabilityNode", capability_node)
    graph.add_node("uiNode", ui_node)
    graph.add_node("componentNode", component_node)
    graph.add_node("structureNode", structure_node)
    graph.add_node("dependencyNode", dependency_node)
    graph.add_node("supabaseSubgraph", run_supabase_graph)
    graph.add_node("typeNode", type_node)
    graph.add_node("utilsNode", utils_node)
    graph.add_node("mockDataNode", mock_data_node)
    graph.add_node("serviceNode", service_node)
    graph.add_node("hooksNode", hooks_node)
    graph.add_node("manifestNode", manifest_node)

    # Step 12-13: Subgraph bridge nodes
    graph.add_node("componentSubgraph", run_component_graph)
    graph.add_node("pageSubgraph", run_page_graph)

    # Step 14: Layout generation node
    graph.add_node("layoutNode", layout_node)

    # Step 15: Style generation node
    graph.add_node("styleGenNode", style_gen_node)

    # Step 15: App.tsx generation node
    graph.add_node("appGenNode", app_gen_node)

    # Step 16: File assembly node
    graph.add_node("assembleNode", assemble_node)

    # Step 17: AST post-processing node
    graph.add_node("postProcessNode", post_process_node)

    # Step 18: Real frontend compile check
    graph.add_node("compileCheckNode", compile_check_node)

    # Step 19: LLM debug fix when compile fails (loops back to compile check)
    graph.add_node("debugFixNode", debug_fix_node)

    # 编排：先分析意图，再决定生成 / 联库问答 / 闲聊
    graph.add_edge(START, "analysisNode")
    graph.add_conditional_edges(
        "analysisNode",
        route_after_analysis,
        {
            "generation": "intentNode",           # 完整生成
            "database_inquiry": "supabaseSubgraph",  # QA+联库：先拉 schema 再 SQL
            "conversational": "chatReplyNode",    # 纯对话，直接结束
        },
    )
    graph.add_edge("supabaseSubgraph", "inquiryNode")
    graph.add_edge("inquiryNode", "chatReplyNode")
    graph.add_edge("chatReplyNode", END)
    graph.add_edge("intentNode", "capabilityNode")
    graph.add_edge("capabilityNode", "uiNode")
    graph.add_edge("uiNode", "componentNode")
    graph.add_edge("componentNode", "structureNode")
    graph.add_edge("structureNode", "dependencyNode")
    graph.add_edge("dependencyNode", "supabaseSubgraph")
    graph.add_edge("supabaseSubgraph", "typeNode")
    graph.add_edge("typeNode", "utilsNode")
    graph.add_edge("utilsNode", "mockDataNode")
    graph.add_edge("mockDataNode", "serviceNode")
    graph.add_edge("serviceNode", "hooksNode")
    graph.add_edge("hooksNode", "manifestNode")
    graph.add_edge("manifestNode", "componentSubgraph")
    graph.add_edge("componentSubgraph", "pageSubgraph")
    graph.add_edge("pageSubgraph", "layoutNode")
    graph.add_edge("layoutNode", "styleGenNode")
    graph.add_edge("styleGenNode", "appGenNode")
    graph.add_edge("appGenNode", "assembleNode")
    graph.add_edge("assembleNode", "postProcessNode")
    graph.add_edge("postProcessNode", "compileCheckNode")
    graph.add_conditional_edges(
        "compileCheckNode",
        route_after_compile_check,
        {"debugFixNode": "debugFixNode", END: END},
    )
    graph.add_edge("debugFixNode", "compileCheckNode")

    return graph.compile(checkpointer=checkpointer)
