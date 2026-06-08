"""
Figma direct flow - Block Extract node.

Converts parsed JSX elements into normalized LayoutBlocks with coordinate info.
"""
from agents.flows.figma_direct.parsing.utils.style_extractor import extract_layout_block


async def block_extract_node(state: dict) -> dict:
    """Convert AST parsed elements to LayoutBlocks with layout info."""
    print("\n[BlockExtractNode] Extracting layout blocks...")

    parsed_blocks = state.get("parsedBlocks", [])
    if not parsed_blocks:
        print("[BlockExtractNode] No parsedBlocks found, skipping")
        return {}

    # Get the first (and usually only) AST output
    ast_output = parsed_blocks[0] if parsed_blocks else {}
    jsx_elements = ast_output.get("jsxElements", [])

    if not jsx_elements:
        print("[BlockExtractNode] No JSX elements found, skipping")
        return {}

    # Convert each JSX element to a LayoutBlock
    layout_blocks = []
    for i, elem in enumerate(jsx_elements):
        block = extract_layout_block(elem, i)
        layout_blocks.append(block)

    # Estimate page height from max(top + height)
    page_height = 0.0
    for block in layout_blocks:
        bottom = block.get("top", 0) + block.get("height", 0)
        if bottom > page_height:
            page_height = bottom

    # Fallback page height
    if page_height == 0:
        page_height = 2000.0

    background_count = sum(1 for b in layout_blocks if b.get("isBackground", False))
    print(f"[BlockExtractNode] Layout blocks: {len(layout_blocks)} ({background_count} backgrounds)")
    print(f"[BlockExtractNode] Page height: {page_height:.0f}px")

    block_extract_output = {
        "layoutBlocks": layout_blocks,
        "pageHeight": page_height,
    }

    return {"blockExtracts": [block_extract_output]}
