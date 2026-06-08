"""step17: AST post-processing node (no LLM)."""
from agents.utils.ast.fixer import post_process_files, print_fix_report
from agents.utils.export_repair import repair_all_exports


async def post_process_node(state: dict) -> dict:
    """Apply AST post-processing to fix common code issues."""
    print("--- PostProcessNode (AST) Start ---")

    assembled_files = state.get("files", {})
    if isinstance(assembled_files, dict):
        file_map = assembled_files.get("files", {})
    else:
        file_map = {}

    if not file_map:
        print("[PostProcess] No files found in state, skipping AST post-processing")
        return {}

    try:
        result_data = post_process_files(file_map)
        fixed_files = result_data["files"]
        result = result_data["result"]

        print_fix_report(result)

        export_stats = repair_all_exports(fixed_files)
        if any(
            export_stats.get(k, 0) > 0
            for k in (
                "reexportsAdded",
                "defaultExportsAdded",
                "namedImportsFixed",
            )
        ):
            print(f"[PostProcess] Export repairs: {export_stats}")

        current_stats = assembled_files.get("stats", {}) if isinstance(assembled_files, dict) else {}
        stats = {
            **(current_stats or {}),
            "astFixes": result.get("totalFixes", 0),
            "astIssues": result.get("totalIssues", 0),
            **export_stats,
        }

        export_fixed = any(export_stats.get(k, 0) > 0 for k in export_stats)
        if result.get("totalFixes", 0) > 0 or export_fixed:
            print(f"[PostProcess] Applied {result.get('totalFixes', 0)} AST fixes")
            return {"files": {"files": fixed_files, "stats": stats}}

        print("[PostProcess] No issues found, files unchanged")
        return {}

    except Exception as e:
        print(f"[PostProcess] AST post-processing failed: {e}")
        print("[PostProcess] Continuing with original files")
        return {}
