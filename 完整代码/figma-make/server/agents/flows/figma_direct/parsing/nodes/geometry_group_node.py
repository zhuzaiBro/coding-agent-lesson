"""
Figma direct flow - Geometry Group node.

Groups LayoutBlocks into semantic sections using Y-axis clustering.
"""
from agents.flows.figma_direct.parsing.utils.geometry_cluster import cluster_by_geometry


async def geometry_group_node(state: dict) -> dict:
    """Group layout blocks into sections by geometry."""
    print("\n[GeometryGroupNode] Clustering blocks into sections...")

    block_extracts = state.get("blockExtracts", [])
    if not block_extracts:
        print("[GeometryGroupNode] No blockExtracts found, skipping")
        return {}

    block_extract = block_extracts[0] if block_extracts else {}
    layout_blocks = block_extract.get("layoutBlocks", [])

    if not layout_blocks:
        print("[GeometryGroupNode] No layout blocks found, skipping")
        return {}

    result = cluster_by_geometry(layout_blocks)
    sections = result.get("sections", [])
    threshold = result.get("threshold", 0)

    print(f"[GeometryGroupNode] Sections: {len(sections)}, Threshold: {threshold:.0f}px")
    for s in sections:
        print(
            f"  Section {s['index']}: {s['totalBlocks']} blocks, "
            f"Y=[{s['topRange']['min']:.0f}, {s['topRange']['max']:.0f}], "
            f"texts={len(s['allTexts'])}"
        )

    return {"geometryGroups": [result]}
