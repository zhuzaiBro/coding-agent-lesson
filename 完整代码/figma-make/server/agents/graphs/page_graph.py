"""
页面并行生成子图（fan-out，与 component_graph 对称）。

structureNode 规划出的 /pages/*.tsx 经 Send 分发到 generatePage 节点并发执行，
生成结果合并为 pagesCode 列表，供 layoutNode / assembleNode 使用。
"""
import json
import operator
from typing import Annotated, Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from agents.flows.traditional.code_generation.prompts.page_gen_prompts import PAGE_GEN_SYSTEM_PROMPT
from agents.flows.traditional.code_generation.schemas.page_gen_schema import PageGenResult
from agents.utils.ast.fixer import process_generated_code
from agents.utils.code_normalizer import normalize_llm_result
from agents.utils.model import get_structured_model


class PageState(TypedDict, total=False):
    """Page subgraph state."""
    pagesToGenerate: List[Dict[str, Any]]
    context: Dict[str, Any]
    targetPage: Optional[Dict[str, Any]]
    pagesCode: Annotated[List[Dict[str, Any]], operator.add]


async def generate_page_node(state: dict) -> dict:
    """Generate a single React page component."""
    target = state.get("targetPage", {})
    context = state.get("context", {})

    if not target:
        print("[PageGraph] No target page provided")
        return {}

    file_path = target.get("path", "/pages/Unknown.tsx")
    print(f"[PageGraph] Generating: {file_path}...")

    hooks = context.get("hooks", {})
    component_result = context.get("componentResult", [])
    types = context.get("types", {})

    components_context = "\n\n".join(
        f"// Component: {c.get('path', '').split('/')[-1].replace('.tsx', '')}\n// File: {c.get('path')}\n{c.get('content', c.get('code', '// No content'))}"
        for c in (component_result or [])
    )

    hooks_context = "\n\n".join(
        f"// Hook: {f.get('path', '').split('/')[-1].replace('.ts', '')}\n// File: {f.get('path')}\n{f.get('content', f.get('code', '// No content'))}"
        for f in (hooks.get("files", []) if hooks else [])
    )

    manifest_text = context.get("projectManifestText") or ""

    user_input = {
        "path": file_path,
        "description": target.get("description", ""),
        "context": {
            "instruction": (
                "Use ONLY symbols listed in projectManifest.modules. "
                "Components: default import. Hooks/services: named imports only. "
                "Do not invent exports or import paths."
            ),
            "projectManifest": manifest_text,
            "library": f"Available Hooks:\n{hooks_context}\n\nAvailable Components:\n{components_context}",
            "availableComponents": [
                {"name": c.get("path", "").split("/")[-1].replace(".tsx", ""), "path": c.get("path")}
                for c in (component_result or [])
            ],
            "availableHooks": [
                {"name": f.get("path", "").split("/")[-1].replace(".ts", ""), "path": f.get("path")}
                for f in (hooks.get("files", []) if hooks else [])
            ],
        },
    }

    model = get_structured_model(PageGenResult)
    result = None

    for attempt in range(1, 4):
        try:
            result = await model.ainvoke([
                SystemMessage(content=PAGE_GEN_SYSTEM_PROMPT),
                HumanMessage(content=json.dumps(user_input, ensure_ascii=False, indent=2)),
            ])
            break
        except Exception as e:
            print(f"[PageGraph] Retry {file_path} ({attempt}/3): {e}")

    if not result:
        print(f"[PageGraph] Failed to generate {file_path}")
        return {}

    result_dict = result.model_dump() if hasattr(result, "model_dump") else result
    result_dict = normalize_llm_result(result_dict)

    if result_dict.get("content"):
        result_dict["content"] = process_generated_code(
            result_dict["content"],
            file_path,
            types.get("files", []) if types else [],
        )

    return {"pagesCode": [result_dict]}


def map_pages(state: dict) -> List[Send]:
    """Fan-out: schedule one generation per page."""
    files = state.get("pagesToGenerate", [])
    unique = list({f.get("path"): f for f in files}.values())
    print(f"[PageGraph] Scheduling {len(unique)} page generations (from {len(files)})")
    return [
        Send("generatePage", {
            "targetPage": f,
            "context": state.get("context", {}),
        })
        for f in unique
    ]


def build_page_graph():
    """Build and compile the page subgraph."""
    graph = StateGraph(PageState)
    graph.add_node("generatePage", generate_page_node)
    graph.add_conditional_edges(START, map_pages, ["generatePage"])
    graph.add_edge("generatePage", END)
    return graph.compile()


page_graph = build_page_graph()
