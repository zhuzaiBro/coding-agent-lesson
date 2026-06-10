"""
Figma 直连流程 - 后处理节点。

对组装完成的 Figma 组件文件执行 AST 自动修复。
"""
from agents.utils.ast.fixer import post_process_files, print_fix_report


async def figma_post_process_node(state: dict) -> dict:
    """对 Figma 流程组装出的文件应用后处理修复。"""
    print("--- FigmaPostProcessNode (AST) 开始 ---")

    assembled = state.get("files", {})
    file_map = assembled.get("files", {}) if isinstance(assembled, dict) else {}

    if not file_map:
        print("[FigmaPostProcess] 未找到文件，跳过")
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
        print(f"[FigmaPostProcess] 后处理失败: {e}")
        return {}
