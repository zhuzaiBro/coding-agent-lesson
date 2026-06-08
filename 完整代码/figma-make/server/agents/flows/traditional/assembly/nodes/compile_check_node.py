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
        print(f"[CompileCheck] Build failed (non-blocking): {error}")
        return {
            "files": {
                "files": file_map,
                "stats": {
                    **(current_stats or {}),
                    "compileChecked": False,
                    "compileError": str(error)[:2000],
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
