"""
Figma direct flow - AST Parser node.

Parses the raw Figma-generated TSX code to extract structural info.
"""
from agents.flows.figma_direct.parsing.utils.jsx_parser import parse_tsx_code


async def ast_parser_node(state: dict) -> dict:
    """Parse raw Figma code into structured AST output."""
    print("\n[AstParserNode] Parsing Figma-generated code...")

    raw_code = state.get("figmaCode", "")
    if not raw_code:
        print("[AstParserNode] No figmaCode found, skipping")
        return {}

    try:
        ast_output = parse_tsx_code(raw_code)

        entry_name = ast_output.get("entryComponentName", "App")
        jsx_count = len(ast_output.get("jsxElements", []))
        assets_count = len(ast_output.get("globalAssets", []))
        helpers_count = len(ast_output.get("helperComponents", []))

        print(f"[AstParserNode] Entry component: {entry_name}")
        print(f"[AstParserNode] JSX elements: {jsx_count}")
        print(f"[AstParserNode] Global assets: {assets_count}")
        print(f"[AstParserNode] Helper components: {helpers_count}")

        return {"parsedBlocks": [ast_output]}
    except Exception as e:
        print(f"[AstParserNode] Parsing failed: {e}")
        raise
