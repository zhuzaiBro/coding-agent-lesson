"""
LangGraph state schema for the main graph.

Uses TypedDict with Annotated for reducer support.
"""
import operator
from typing import Annotated, Any, Dict, List, Optional

from typing_extensions import TypedDict


class GraphState(TypedDict, total=False):
    """
    Main graph state definition.

    Fields with Annotated[list, operator.add] support fan-in (parallel node results merge).
    """
    # Initial input: chat history
    messages: List[Any]

    # Initial input: Mock config for nodes
    mockConfig: Optional[Dict[str, bool]]

    # Text prompt (legacy)
    textPrompt: Optional[str]

    # Figma URL (figma flow)
    figmaUrl: Optional[str]

    # step0: behavior analysis
    analysis: Optional[Dict[str, Any]]

    # step0.5: control flow flag
    skipGeneration: Optional[bool]

    # step1: intent details
    intent: Optional[Dict[str, Any]]

    # step2: capability analysis
    capabilities: Optional[Dict[str, Any]]

    # step3: UI architecture
    ui: Optional[Dict[str, Any]]

    # step4: component contracts
    components: Optional[Dict[str, Any]]

    # step5: project structure
    structure: Optional[Dict[str, Any]]

    # step6: dependency management
    dependency: Optional[Dict[str, Any]]

    # step7: type definitions
    types: Optional[Dict[str, Any]]

    # step8: utility function files
    utils: Optional[Dict[str, Any]]

    # step9: mock data
    mockData: Optional[Dict[str, Any]]

    # step10: service layer files
    service: Optional[Dict[str, Any]]

    # step11: hooks layer files
    hooks: Optional[Dict[str, Any]]

    # step11.5: generated module/export/import DSL
    projectManifest: Optional[Dict[str, Any]]
    projectManifestText: Optional[str]

    # step12: UI component code (fan-in from component subgraph)
    componentsCode: Annotated[List[Dict[str, Any]], operator.add]

    # step13: generated page code (fan-in from page subgraph)
    pagesCode: Annotated[List[Dict[str, Any]], operator.add]

    # step14: Layout node output
    layouts: Optional[Dict[str, Any]]

    # step15: global styles
    styles: Optional[Dict[str, Any]]

    # step15: App.tsx entry file
    app: Optional[Dict[str, Any]]

    # step16: assembled files (Sandpack format)
    files: Optional[Dict[str, Any]]

    # --- Figma flow specific ---
    # Raw figma code from MCP
    figmaCode: Optional[str]

    # Downloaded images map: {url: bytes}
    downloadedImages: Optional[Dict[str, bytes]]

    # Parsed AST blocks
    parsedBlocks: Optional[List[Dict[str, Any]]]

    # Block extracts (layout, texts, assets)
    blockExtracts: Optional[List[Dict[str, Any]]]

    # Geometry groups
    geometryGroups: Optional[List[Dict[str, Any]]]

    # Named sections
    namedSections: Optional[List[Dict[str, Any]]]

    # Generated components code
    figmaComponents: Optional[List[Dict[str, Any]]]
