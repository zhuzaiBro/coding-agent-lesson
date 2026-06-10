"""
Figma 直连流程 - 输入节点。

通过 Figma MCP Server 根据 Figma 设计链接获取自动生成的 UI 代码。
"""


async def figma_input_node(state: dict) -> dict:
    """从 Figma MCP Server 拉取生成的代码。"""
    print("\n" + "=" * 80)
    print("[FigmaInputNode] 开始获取 Figma 代码")
    print("=" * 80)

    figma_url = state.get("figmaUrl")

    if not figma_url:
        raise ValueError("FigmaInputNode: 缺少 figmaUrl，请提供 Figma 设计链接")

    print(f"[FigmaInputNode] Figma URL: {figma_url}")

    # 调用 MCP Server
    try:
        from services.figma.mcp_client import get_figma_mcp_client
        print("[FigmaInputNode] 正在调用 Figma MCP Server...")
        print("   （首次连接可能需要数秒，代码生成通常需要 1-3 分钟）")

        client = get_figma_mcp_client()
        raw_code = await client.get_generated_code(figma_url)
    except Exception as e:
        raise RuntimeError(
            f"Figma MCP Server 调用失败: {e}\n"
            "请确认：\n"
            "1. Figma Desktop 已打开并已登录\n"
            "2. 设计文件已在 Figma Desktop 中打开\n"
            "3. MCP Server 正在运行 (http://127.0.0.1:3845/mcp)"
        )

    if not raw_code or not raw_code.strip():
        raise ValueError("Figma MCP Server 返回空代码，请检查设计是否有效")

    # 检测 MCP 返回的错误提示（而非代码）
    error_patterns = [
        "The MCP server is only available if your active tab",
        "is only available if",
        "Unable to",
        "Cannot find",
        "No node found",
    ]
    is_error = len(raw_code.split("\n")) <= 3 and any(p in raw_code for p in error_patterns)
    if is_error:
        raise ValueError(f"Figma MCP Server 返回错误而非代码:\n\"{raw_code}\"")

    # 校验内容是否像有效代码
    has_code_features = any(kw in raw_code for kw in ["import ", "export ", "function ", "const ", "return (", "<div"])
    if len(raw_code) < 200 or not has_code_features:
        raise ValueError(
            f"Figma MCP Server 返回内容不像有效代码（{len(raw_code)} 字符）。\n"
            f"预览: \"{raw_code[:100]}...\""
        )

    code_length = len(raw_code)
    line_count = raw_code.count("\n") + 1

    print(f"\n[FigmaInputNode] 代码获取成功")
    print(f"  字符数: {code_length:,}")
    print(f"  行数: {line_count:,}")
    print(f"  预览: {raw_code[:200]}...")
    print("")

    return {
        "figmaCode": raw_code,
        "codeLength": code_length,
        "lineCount": line_count,
    }
