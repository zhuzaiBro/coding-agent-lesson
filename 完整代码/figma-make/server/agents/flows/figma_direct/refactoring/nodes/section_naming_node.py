"""
Figma direct flow - Section Naming node.

Uses AI to give semantic names to each section.
"""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.flows.figma_direct.refactoring.prompts.section_naming_prompts import (
    get_section_naming_human_prompt,
    get_section_naming_system_prompt,
)
from agents.flows.figma_direct.refactoring.schemas.refactoring_schema import SectionNamingOutput
from agents.utils.model import get_structured_model
from agents.utils.retry import with_retry


async def section_naming_node(state: dict) -> dict:
    """Name sections using AI based on content and structure."""
    print("\n[SectionNamingNode] Naming sections with AI...")

    geometry_groups = state.get("geometryGroups", [])
    if not geometry_groups:
        print("[SectionNamingNode] No geometry groups found, skipping")
        return {}

    geo_group = geometry_groups[0] if geometry_groups else {}
    sections = geo_group.get("sections", [])

    if not sections:
        print("[SectionNamingNode] No sections found, skipping")
        return {}

    # Prepare sections info for the prompt
    sections_info = []
    for s in sections:
        sections_info.append({
            "index": s.get("index", 0),
            "totalBlocks": s.get("totalBlocks", 0),
            "topRange": s.get("topRange", {"min": 0, "max": 0}),
            "allTexts": s.get("allTexts", []),
            "allAssets": s.get("allAssets", []),
            "hasBackground": len(s.get("backgroundBlocks", [])) > 0,
        })

    structured_model = get_structured_model(SectionNamingOutput)

    system_prompt = get_section_naming_system_prompt()
    human_prompt = get_section_naming_human_prompt(sections_info)

    prompt = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ]

    result = await with_retry(
        structured_model,
        prompt,
        max_retries=3,
        on_retry=lambda attempt, err: print(f"[SectionNamingNode] Retry {attempt}: {err}"),
    )

    result_dict = result.model_dump() if hasattr(result, "model_dump") else result
    named_sections = result_dict.get("namedSections", [])

    print(f"[SectionNamingNode] Named {len(named_sections)} sections:")
    for ns in named_sections:
        print(f"  Section {ns.get('index')}: {ns.get('componentName')} - {ns.get('description')}")

    return {"namedSections": named_sections}
