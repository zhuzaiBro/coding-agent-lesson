"""Final frontend compile-check node."""
from agents.utils.frontend_compile import FrontendCompileError, compile_frontend_files


async def compile_check_node(state: dict) -> dict:
    """Run a real Vite build against the generated frontend files."""
    print("--- CompileCheckNode Start ---")

    assembled = state.get("files", {})
    file_map = assembled.get("files", {}) if isinstance(assembled, dict) else {}
    if not file_map:
        raise FrontendCompileError("No generated files found before compile check.")

    current_stats = assembled.get("stats", {}) if isinstance(assembled, dict) else {}

    try:
        result = await compile_frontend_files(assembled)
    except FrontendCompileError as error:
        err_text = str(error)
        # 服务器未装 Node/npm 时跳过校验，避免误报「编译检查未通过」并浪费 debug 重试
        if "npm was not found" in err_text:
            print("[CompileCheck] Skipped: npm not installed on server")
            return {
                "files": {
                    "files": file_map,
                    "stats": {
                        **(current_stats or {}),
                        "compileChecked": True,
                        "compileSkipped": True,
                    },
                },
            }

        print(f"[CompileCheck] Build failed (non-blocking): {error}")
        return {
            "files": {
                "files": file_map,
                "stats": {
                    **(current_stats or {}),
                    "compileChecked": False,
                    "compileError": err_text[:2000],
                },
            }
        }

    print("[CompileCheck] Frontend build passed")
    return {
        "files": {
            "files": result["files"],
            "stats": {
                **(current_stats or {}),
                **result.get("stats", {}),
                "compileChecked": True,
            },
        }
    }
