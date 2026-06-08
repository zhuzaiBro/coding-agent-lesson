"""
Figma direct flow - Input node.

Calls Figma MCP Server to get generated UI code from a Figma URL.
"""


async def figma_input_node(state: dict) -> dict:
    """Fetch generated code from Figma MCP Server."""
    print("\n" + "=" * 80)
    print("[FigmaInputNode] Starting Figma code retrieval")
    print("=" * 80)

    figma_url = state.get("figmaUrl")

    if not figma_url:
        raise ValueError("FigmaInputNode: Missing figmaUrl, please provide a Figma design link")

    print(f"[FigmaInputNode] Figma URL: {figma_url}")

    # Call MCP Server
    try:
        from services.figma.mcp_client import get_figma_mcp_client
        print("[FigmaInputNode] Calling Figma MCP Server...")
        print("   (First connection may take a few seconds, code generation may take 1-3 minutes)")

        client = get_figma_mcp_client()
        raw_code = await client.get_generated_code(figma_url)
    except Exception as e:
        raise RuntimeError(
            f"Figma MCP Server call failed: {e}\n"
            "Please ensure:\n"
            "1. Figma Desktop is open and logged in\n"
            "2. The design file is open in Figma Desktop\n"
            "3. MCP Server is running (http://127.0.0.1:3845/mcp)"
        )

    if not raw_code or not raw_code.strip():
        raise ValueError("Figma MCP Server returned empty code, please check if the design is valid")

    # Check for error messages
    error_patterns = [
        "The MCP server is only available if your active tab",
        "is only available if",
        "Unable to",
        "Cannot find",
        "No node found",
    ]
    is_error = len(raw_code.split("\n")) <= 3 and any(p in raw_code for p in error_patterns)
    if is_error:
        raise ValueError(f"Figma MCP Server returned an error instead of code:\n\"{raw_code}\"")

    # Validate it looks like code
    has_code_features = any(kw in raw_code for kw in ["import ", "export ", "function ", "const ", "return (", "<div"])
    if len(raw_code) < 200 or not has_code_features:
        raise ValueError(
            f"Figma MCP Server content doesn't look like valid code ({len(raw_code)} chars).\n"
            f"Preview: \"{raw_code[:100]}...\""
        )

    code_length = len(raw_code)
    line_count = raw_code.count("\n") + 1

    print(f"\n[FigmaInputNode] Code retrieval successful")
    print(f"  Characters: {code_length:,}")
    print(f"  Lines: {line_count:,}")
    print(f"  Preview: {raw_code[:200]}...")
    print("")

    return {
        "figmaCode": raw_code,
        "codeLength": code_length,
        "lineCount": line_count,
    }
