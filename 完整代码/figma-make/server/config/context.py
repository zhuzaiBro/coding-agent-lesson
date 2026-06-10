"""Agent 对话上下文窗口配置（环境变量）。"""
import os


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def is_context_compression_enabled() -> bool:
    return os.getenv("CONTEXT_COMPRESSION_ENABLED", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def get_context_max_tokens() -> int:
    """上下文预算（估算 token，默认约 24k）。"""
    return max(2000, _int_env("CONTEXT_WINDOW_MAX_TOKENS", 24000))


def get_context_keep_recent_messages() -> int:
    """压缩时保留的最近消息条数（含 user/assistant）。"""
    return max(2, _int_env("CONTEXT_KEEP_RECENT_MESSAGES", 8))


def get_context_summary_max_chars() -> int:
    """摘要最大字符数，防止摘要本身撑爆窗口。"""
    return max(500, _int_env("CONTEXT_SUMMARY_MAX_CHARS", 3000))
