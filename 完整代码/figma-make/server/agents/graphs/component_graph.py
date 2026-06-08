"""
组件并行生成子图（fan-out 模式）

将所有待生成的组件文件通过 LangGraph Send 分发到独立的 generateComponent 节点，
各节点并发运行、各自调用 LLM，完成后通过 path-based reducer 去重合并回主图。

对比串行：如果有 10 个组件，并行模式节省约 90% 的等待时间。
"""
import json
import operator
from typing import Annotated, Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from agents.flows.traditional.code_generation.prompts.comp_gen_prompts import COMP_GEN_SYSTEM_PROMPT
from agents.flows.traditional.code_generation.schemas.comp_gen_schema import CompGenResult
from agents.utils.ast.fixer import process_generated_code
from agents.utils.code_normalizer import normalize_llm_result
from agents.utils.model import get_structured_model


class ComponentState(TypedDict, total=False):
    """Component subgraph state."""
    componentsToGenerate: List[Dict[str, Any]]
    context: Dict[str, Any]
    targetComponent: Optional[Dict[str, Any]]
    componentsCode: Annotated[List[Dict[str, Any]], operator.add]


def _path_based_reducer(existing: List, new_items: List) -> List:
    """Merge components by path, later result overwrites earlier."""
    merged = {item.get("path", i): item for i, item in enumerate(existing)}
    for item in new_items:
        key = item.get("path", len(merged))
        merged[key] = item
    return list(merged.values())


async def generate_component_node(state: dict) -> dict:
    """Generate a single React component."""
    target = state.get("targetComponent", {})
    context = state.get("context", {})

    if not target:
        print("[ComponentGraph] No target component provided")
        return {}

    file_path = target.get("path", "/components/Unknown.tsx")
    file_name = file_path.split("/")[-1]
    print(f"[ComponentGraph] Generating: {file_name}...")

    hooks = context.get("hooks", {})
    types = context.get("types", {})
    components = context.get("components", {})

    type_context = "\n\n".join(
        f"// File: {f.get('path')}\n{f.get('code', '')}"
        for f in (types.get("files", []) if types else [])
    )

    hooks_context = "\n\n".join(
        f"// File: {f.get('path')}\n{f.get('content', '')}"
        for f in (hooks.get("files", []) if hooks else [])
    )

    comp_specs = (components.get("components", []) if components else [])
    comp_spec = next(
        (c for c in comp_specs if file_name.replace(".tsx", "") in c.get("componentId", "")),
        {"componentId": "Unknown", "props": [], "events": [], "description": target.get("description", "")},
    )

    manifest_text = context.get("projectManifestText") or ""

    user_prompt = f"""Current task: Generate component file "{file_path}"

Project Manifest DSL (only import symbols/paths listed here):
{manifest_text or '(not available)'}

Component Spec:
ID: {comp_spec.get('componentId')}
Description: {comp_spec.get('description', target.get('description', ''))}
Props: {json.dumps(comp_spec.get('props', []))}
Events: {json.dumps(comp_spec.get('events', []))}

Available Hooks (import ONLY from these files — copy exact path stem):
{hooks_context or '(none)'}

Available Types (import ONLY from these files):
{type_context or '(none)'}

Requirements:
- Complete React component with Tailwind CSS
- Import hooks/types ONLY from the files above; do NOT import ../services/*
- Do NOT invent hook or type module names
- No hardcoded mock data; no extra npm packages
- MUST use `export default <ComponentName>` where ComponentName matches the file basename (default export, not named-only export)
- When importing other components from the library, use default import: `import Foo from '../components/Foo'`
"""

    model = get_structured_model(CompGenResult)
    result = None

    for attempt in range(1, 4):
        try:
            result = await model.ainvoke([
                SystemMessage(content=COMP_GEN_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ])
            break
        except Exception as e:
            print(f"[ComponentGraph] Retry {file_name} ({attempt}/3): {e}")

    if not result:
        print(f"[ComponentGraph] Failed to generate {file_name}")
        return {}

    result_dict = result.model_dump() if hasattr(result, "model_dump") else result
    result_dict = normalize_llm_result(result_dict)

    if result_dict.get("content"):
        result_dict["content"] = process_generated_code(
            result_dict["content"],
            file_path,
            types.get("files", []) if types else [],
        )

    return {"componentsCode": [result_dict]}


def map_components(state: dict) -> List[Send]:
    """Fan-out: schedule one generation per component."""
    files = state.get("componentsToGenerate", [])
    # Deduplicate by path
    unique = list({f.get("path"): f for f in files}.values())
    print(f"[ComponentGraph] Scheduling {len(unique)} component generations (from {len(files)})")
    return [
        Send("generateComponent", {
            "targetComponent": f,
            "context": state.get("context", {}),
        })
        for f in unique
    ]


def build_component_graph():
    """Build and compile the component subgraph."""
    graph = StateGraph(ComponentState)
    graph.add_node("generateComponent", generate_component_node)
    graph.add_conditional_edges(START, map_components, ["generateComponent"])
    graph.add_edge("generateComponent", END)
    return graph.compile()


component_graph = build_component_graph()
