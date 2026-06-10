"""
Supabase MCP 连接配置。

认证优先级：当前请求 OAuth token（中间件注入）> 环境变量 PAT。
build_mcp_url 根据 project_ref、read_only、features 拼装 MCP 端点 URL。
"""
from contextvars import ContextVar
import os
from typing import Optional
from urllib.parse import urlencode

# 由中间件注入：当前 HTTP 请求对应的 OAuth session
_request_oauth_session_id: ContextVar[Optional[str]] = ContextVar(
    "supabase_oauth_session_id", default=None
)
_request_oauth_access_token: ContextVar[Optional[str]] = ContextVar(
    "supabase_oauth_access_token", default=None
)

OAUTH_COOKIE = "zood_supabase_sid"


def set_request_oauth_context(
    session_id: Optional[str], access_token: Optional[str]
) -> None:
    _request_oauth_session_id.set(session_id)
    _request_oauth_access_token.set(access_token)


def get_request_oauth_session_id() -> Optional[str]:
    return _request_oauth_session_id.get()


def is_supabase_configured() -> bool:
    """OAuth 会话或 PAT 任一可用即可。"""
    return bool(get_access_token())


def get_access_token() -> str:
    oauth_token = _request_oauth_access_token.get()
    if oauth_token:
        return oauth_token
    return (
        os.getenv("SUPABASE_ACCESS_TOKEN", "").strip()
        or os.getenv("SUPABASE_PAT", "").strip()
    )


def get_project_ref() -> str:
    return os.getenv("SUPABASE_PROJECT_REF", "").strip()


def is_read_only() -> bool:
    return os.getenv("SUPABASE_MCP_READ_ONLY", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def get_features() -> Optional[str]:
    """Optional comma-separated MCP feature groups, e.g. database,docs."""
    value = os.getenv("SUPABASE_MCP_FEATURES", "").strip()
    return value or None


def build_mcp_url() -> str:
    """Remote Supabase MCP URL with project scoping."""
    base = os.getenv("SUPABASE_MCP_URL", "https://mcp.supabase.com/mcp").strip()
    if "?" in base:
        root, query = base.split("?", 1)
        params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
    else:
        root = base.rstrip("/")
        params = {}

    project_ref = get_project_ref()
    if project_ref and "project_ref" not in params:
        params["project_ref"] = project_ref
    if is_read_only() and "read_only" not in params:
        params["read_only"] = "true"
    features = get_features()
    if features and "features" not in params:
        params["features"] = features

    if not params:
        return root
    return f"{root}?{urlencode(params)}"
