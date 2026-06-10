"""
Figma 直连流程 - AST 解析节点。

解析 Figma 生成的原始 TSX 代码，提取结构信息。
"""
from agents.flows.figma_direct.parsing.utils.jsx_parser import parse_tsx_code


async def ast_parser_node(state: dict) -> dict:
    """将原始 Figma 代码解析为结构化 AST 输出。"""
    print("\n[AstParserNode] 正在解析 Figma 生成的代码...")

    raw_code = state.get("figmaCode", "")
    if not raw_code:
        print("[AstParserNode] 未找到 figmaCode，跳过")
        return {}

    try:
        ast_output = parse_tsx_code(raw_code)

        entry_name = ast_output.get("entryComponentName", "App")
        jsx_count = len(ast_output.get("jsxElements", []))
        assets_count = len(ast_output.get("globalAssets", []))
        helpers_count = len(ast_output.get("helperComponents", []))

        print(f"[AstParserNode] 入口组件: {entry_name}")
        print(f"[AstParserNode] JSX 元素: {jsx_count}")
        print(f"[AstParserNode] 全局资源: {assets_count}")
        print(f"[AstParserNode] 辅助组件: {helpers_count}")

        return {"parsedBlocks": [ast_output]}
    except Exception as e:
        print(f"[AstParserNode] 解析失败: {e}")
        raise
