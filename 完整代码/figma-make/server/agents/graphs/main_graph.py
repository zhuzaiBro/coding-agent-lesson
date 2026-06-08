"""
Main graph (routing dispatcher).

Returns the appropriate generation graph based on mode:
- "figma"         → Figma direct graph (figma_graph.py)
- "traditional"   → Traditional graph (traditional_graph.py)
- "modification"  → User edit graph (modification_graph.py)

Responsibilities:
1. Provide build_agent(mode) factory function
2. Re-export shared URL detection utility for backwards compatibility
"""
from typing import Literal

from agents.graphs.traditional_graph import build_traditional_agent
from agents.graphs.figma_graph import build_figma_agent
from agents.graphs.modification_graph import build_modification_agent
from agents.shared.utils.figma_url import extract_figma_url

__all__ = ["build_agent", "extract_figma_url"]


def build_agent(mode: Literal["traditional", "figma", "modification"] = "traditional"):
    """
    Build an Agent.

    Args:
        mode: Specifies the mode.
            - "traditional": Prompt-driven multi-step code generation.
            - "figma": Figma MCP direct connect code split flow.

    Returns:
        A compiled LangGraph graph ready to invoke.
    """
    if mode == "figma":
        print("[MainGraph] Building Figma direct graph")
        return build_figma_agent()

    if mode == "modification":
        print("[MainGraph] Building Modification graph")
        return build_modification_agent()

    print("[MainGraph] Building Traditional graph")
    return build_traditional_agent()
