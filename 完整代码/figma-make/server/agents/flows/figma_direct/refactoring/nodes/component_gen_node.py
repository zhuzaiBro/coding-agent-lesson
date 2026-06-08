"""
Figma direct flow - Component Generation node.

Generates React components for each named section using AI.
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
    """Get the raw JSX for a section (combined from its blocks)."""
    section = next((s for s in sections if s.get("index") == section_index), None)
    if not section:
        return ""

    blocks = section.get("blocks", [])
    jsxs = [b.get("rawJsx", "") for b in blocks if b.get("rawJsx")]
    return "\n\n".join(jsxs[:5])  # Limit to first 5 blocks for token efficiency


async def component_gen_node(state: dict) -> dict:
    """Generate React component code for each named section."""
    print("\n[ComponentGenNode] Generating component code...")

    named_sections = state.get("namedSections", [])
    geometry_groups = state.get("geometryGroups", [])
    parsed_blocks = state.get("parsedBlocks", [])

    if not named_sections:
        print("[ComponentGenNode] No named sections, skipping")
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

        print(f"\n[ComponentGenNode] Generating: {component_name} (section {section_index})")

        # Get JSX for this section
        raw_jsx = _get_section_jsx(sections, section_index)

        if not raw_jsx:
            print(f"[ComponentGenNode] No JSX found for section {section_index}, skipping")
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
                on_retry=lambda attempt, err: print(f"[ComponentGenNode] Retry {attempt}: {err}"),
            )
            result_dict = result.model_dump() if hasattr(result, "model_dump") else result
            generated_file = result_dict.get("file", {})
            print(f"[ComponentGenNode] Generated: {generated_file.get('filePath', 'unknown')}")
            generated_components.append(result_dict)
        except Exception as e:
            print(f"[ComponentGenNode] Failed to generate {component_name}: {e}")

    print(f"\n[ComponentGenNode] Generated {len(generated_components)} components")
    return {"figmaComponents": generated_components}
