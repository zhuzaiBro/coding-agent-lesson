"""
Figma 直连流程 - 组件生成节点。

为每个已命名的 Section 调用 LLM 生成可维护的 React 组件代码。
"""
from langchain_core.messages import HumanMessage, SystemMessage

from agents.flows.figma_direct.refactoring.prompts.component_gen_prompts import (
    get_component_gen_human_prompt,
    get_component_gen_system_prompt,
)
from agents.flows.figma_direct.refactoring.schemas.refactoring_schema import ComponentGenResult
from agents.utils.model import get_structured_model
from agents.utils.retry import with_retry


def _get_section_jsx(sections: list, section_index: int) -> str:
    """获取指定 Section 的原始 JSX（合并其布局块）。"""
    section = next((s for s in sections if s.get("index") == section_index), None)
    if not section:
        return ""

    blocks = section.get("blocks", [])
    jsxs = [b.get("rawJsx", "") for b in blocks if b.get("rawJsx")]
    return "\n\n".join(jsxs[:5])  # 最多取前 5 个块以控制 token 用量


async def component_gen_node(state: dict) -> dict:
    """为每个已命名 Section 生成 React 组件代码。"""
    print("\n[ComponentGenNode] 正在生成组件代码...")

    named_sections = state.get("namedSections", [])
    geometry_groups = state.get("geometryGroups", [])
    parsed_blocks = state.get("parsedBlocks", [])

    if not named_sections:
        print("[ComponentGenNode] 未找到 namedSections，跳过")
        return {"figmaComponents": []}

    geo_group = geometry_groups[0] if geometry_groups else {}
    sections = geo_group.get("sections", [])

    ast_output = parsed_blocks[0] if parsed_blocks else {}
    global_assets = ast_output.get("globalAssets", [])
    helper_components = ast_output.get("helperComponents", [])

    structured_model = get_structured_model(ComponentGenResult)
    system_prompt = get_component_gen_system_prompt()

    generated_components = []

    for named_section in named_sections:
        section_index = named_section.get("index", 0)
        component_name = named_section.get("componentName", f"Section{section_index}")
        description = named_section.get("description", "")

        print(f"\n[ComponentGenNode] 正在生成: {component_name}（Section {section_index}）")

        # 获取该 Section 的 JSX
        raw_jsx = _get_section_jsx(sections, section_index)

        if not raw_jsx:
            print(f"[ComponentGenNode] Section {section_index} 无 JSX，跳过")
            continue

        human_prompt = get_component_gen_human_prompt(
            component_name=component_name,
            description=description,
            raw_jsx=raw_jsx,
            available_assets=global_assets,
            helper_components=helper_components if section_index == 0 else None,
        )

        prompt = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ]

        try:
            result = await with_retry(
                structured_model,
                prompt,
                max_retries=3,
                on_retry=lambda attempt, err: print(f"[ComponentGenNode] 重试 {attempt}: {err}"),
            )
            result_dict = result.model_dump() if hasattr(result, "model_dump") else result
            generated_file = result_dict.get("file", {})
            print(f"[ComponentGenNode] 已生成: {generated_file.get('filePath', 'unknown')}")
            generated_components.append(result_dict)
        except Exception as e:
            print(f"[ComponentGenNode] 生成 {component_name} 失败: {e}")

    print(f"\n[ComponentGenNode] 共生成 {len(generated_components)} 个组件")
    return {"figmaComponents": generated_components}
