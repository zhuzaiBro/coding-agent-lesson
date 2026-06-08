"""
Figma direct flow - Post-process node.

Applies AST fixes to assembled Figma components.
"""
from agents.utils.ast.fixer import post_process_files, print_fix_report


async def figma_post_process_node(state: dict) -> dict:
    """Apply post-processing fixes to Figma flow assembled files."""
    print("--- FigmaPostProcessNode (AST) Start ---")

    assembled = state.get("files", {})
    file_map = assembled.get("files", {}) if isinstance(assembled, dict) else {}

    if not file_map:
        print("[FigmaPostProcess] No files found, skipping")
        return {}

    try:
        result_data = post_process_files(file_map)
        fixed_files = result_data["files"]
        result = result_data["result"]

        print_fix_report(result)

        if result.get("totalFixes", 0) > 0:
            current_stats = assembled.get("stats", {}) if isinstance(assembled, dict) else {}
            return {
                "files": {
                    "files": fixed_files,
                    "stats": {
                        **(current_stats or {}),
                        "astFixes": result["totalFixes"],
                    },
                }
            }

        return {}
    except Exception as e:
        print(f"[FigmaPostProcess] Post-processing failed: {e}")
        return {}
