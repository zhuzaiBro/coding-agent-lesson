"""
Figma 直连流程 - 布局块提取节点。

将解析出的 JSX 元素转换为带坐标信息的规范化 LayoutBlock。
"""
from agents.flows.figma_direct.parsing.utils.style_extractor import extract_layout_block


async def block_extract_node(state: dict) -> dict:
    """将 AST 解析结果转换为带布局信息的 LayoutBlock。"""
    print("\n[BlockExtractNode] 正在提取布局块...")

    parsed_blocks = state.get("parsedBlocks", [])
    if not parsed_blocks:
        print("[BlockExtractNode] 未找到 parsedBlocks，跳过")
        return {}

    # 取第一个（通常也是唯一的）AST 输出
    ast_output = parsed_blocks[0] if parsed_blocks else {}
    jsx_elements = ast_output.get("jsxElements", [])

    if not jsx_elements:
        print("[BlockExtractNode] 未找到 JSX 元素，跳过")
        return {}

    # 将每个 JSX 元素转为 LayoutBlock
    layout_blocks = []
    for i, elem in enumerate(jsx_elements):
        block = extract_layout_block(elem, i)
        layout_blocks.append(block)

    # 根据 max(top + height) 估算页面高度
    page_height = 0.0
    for block in layout_blocks:
        bottom = block.get("top", 0) + block.get("height", 0)
        if bottom > page_height:
            page_height = bottom

    # 页面高度兜底值
    if page_height == 0:
        page_height = 2000.0

    background_count = sum(1 for b in layout_blocks if b.get("isBackground", False))
    print(f"[BlockExtractNode] 布局块: {len(layout_blocks)}（其中 {background_count} 个背景）")
    print(f"[BlockExtractNode] 页面高度: {page_height:.0f}px")

    block_extract_output = {
        "layoutBlocks": layout_blocks,
        "pageHeight": page_height,
    }

    return {"blockExtracts": [block_extract_output]}
