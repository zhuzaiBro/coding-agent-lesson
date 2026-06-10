"""
compileCheckNode 之后的路由。

编译通过 → END；失败且未超重试次数 → debugFixNode（LLM 修代码）→ 再次 compileCheck。
受 ENABLE_COMPILE_DEBUG_FIX 与 FRONTEND_COMPILE_FIX_MAX_RETRIES 控制。
"""
import os

from langgraph.graph import END


def _max_attempts() -> int:
    try:
        return max(0, int(os.getenv("FRONTEND_COMPILE_FIX_MAX_RETRIES", "2")))
    except ValueError:
        return 2


def _debug_fix_enabled() -> bool:
    return os.getenv("ENABLE_COMPILE_DEBUG_FIX", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def route_after_compile_check(state: dict) -> str:
    """根据 files.stats 中的编译结果决定继续修还是结束。"""
    assembled = state.get("files") or {}
    stats = assembled.get("stats") if isinstance(assembled, dict) else {}
    if not isinstance(stats, dict):
        return END

    if stats.get("compileChecked"):
        return END

    if not _debug_fix_enabled():
        return END

    compile_error = stats.get("compileError")
    if not compile_error:
        return END

    attempts = int(stats.get("compileFixAttempts") or 0)
    if attempts < _max_attempts():
        return "debugFixNode"

    return END
