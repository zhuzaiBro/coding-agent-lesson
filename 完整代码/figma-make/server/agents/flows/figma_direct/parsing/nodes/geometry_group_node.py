"""
Figma 直连流程 - 几何分组节点。

按 Y 轴聚类将 LayoutBlock 分组为语义化的 Section。
"""
from agents.flows.figma_direct.parsing.utils.geometry_cluster import cluster_by_geometry


async def geometry_group_node(state: dict) -> dict:
    """按几何位置将布局块分组为 Section。"""
    print("\n[GeometryGroupNode] 正在将布局块聚类为 Section...")

    block_extracts = state.get("blockExtracts", [])
    if not block_extracts:
        print("[GeometryGroupNode] 未找到 blockExtracts，跳过")
        return {}

    block_extract = block_extracts[0] if block_extracts else {}
    layout_blocks = block_extract.get("layoutBlocks", [])

    if not layout_blocks:
        print("[GeometryGroupNode] 未找到布局块，跳过")
        return {}

    result = cluster_by_geometry(layout_blocks)
    sections = result.get("sections", [])
    threshold = result.get("threshold", 0)

    print(f"[GeometryGroupNode] Section 数量: {len(sections)}，阈值: {threshold:.0f}px")
    for s in sections:
        print(
            f"  Section {s['index']}: {s['totalBlocks']} 个块, "
            f"Y=[{s['topRange']['min']:.0f}, {s['topRange']['max']:.0f}], "
            f"文本数={len(s['allTexts'])}"
        )

    return {"geometryGroups": [result]}
