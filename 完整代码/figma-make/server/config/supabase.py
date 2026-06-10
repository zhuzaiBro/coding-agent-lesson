"""
Supabase MCP 连接配置。

认证优先级：当前请求 OAuth token（中间件注入）> 环境变量 PAT。
build_mcp_url 根据 project_ref、read_only、features 拼装 MCP 端点 URL。

注意：OAuth 只解决「谁有权限」，MCP 仍须 project_ref 才能 list_tables / execute_sql。
可在 server/.env 设置 SUPABASE_PROJECT_REF，或由客户端首次 get_project_url 自动解析。
"""
from contextvars import ContextVar
import os
import re
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

# OAuth 会话内从 get_project_url 解析出的 project_ref（进程级缓存）
_runtime_project_ref: Optional[str] = None

# 由中间件注入：当前 OAuth 会话用户选择的项目 ref
_request_oauth_project_ref: ContextVar[Optional[str]] = ContextVar(
    "supabase_oauth_project_ref", default=None
)


def set_request_oauth_context(
    session_id: Optional[str],
    access_token: Optional[str],
    project_ref: Optional[str] = None,
) -> None:
    _request_oauth_session_id.set(session_id)
    _request_oauth_access_token.set(access_token)
    _request_oauth_project_ref.set(
        (project_ref or "").strip() or None
    )


def get_request_oauth_session_id() -> Optional[str]:
    return _request_oauth_session_id.get()


def extract_project_ref_from_url(url: str) -> Optional[str]:
    """从 https://{ref}.supabase.co 提取 project_ref。"""
    text = (url or "").strip()
    match = re.search(r"https?://([a-z0-9]{10,30})\.supabase\.co", text, re.IGNORECASE)
    return match.group(1) if match else None


def set_runtime_project_ref(project_ref: str) -> None:
    global _runtime_project_ref
    ref = (project_ref or "").strip()
    if ref:
        _runtime_project_ref = ref
        print(f"[Supabase] 运行时 project_ref={ref}")


def clear_runtime_project_ref() -> None:
    global _runtime_project_ref
    _runtime_project_ref = None


def get_project_ref() -> str:
    explicit = os.getenv("SUPABASE_PROJECT_REF", "").strip()
    if explicit:
        return explicit
    session_ref = _request_oauth_project_ref.get()
    if session_ref:
        return str(session_ref).strip()
    return (_runtime_project_ref or "").strip()


def has_project_ref() -> bool:
    return bool(get_project_ref())


def is_supabase_configured() -> bool:
    """OAuth 会话或 PAT 任一可用即可（仅表示已授权，不代表 MCP 已绑定项目）。"""
    return bool(get_access_token())


def is_supabase_ready() -> bool:
    """已授权且已配置/解析 project_ref。"""
    return is_supabase_configured() and has_project_ref()


def get_access_token() -> str:
    oauth_token = _request_oauth_access_token.get()
    if oauth_token:
        return oauth_token
    return (
        os.getenv("SUPABASE_ACCESS_TOKEN", "").strip()
        or os.getenv("SUPABASE_PAT", "").strip()
    )


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
    return value or "database,docs"


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


def build_org_mcp_url() -> str:
    """账号级 MCP URL（不含 project_ref），用于 list_projects。"""
    base = os.getenv("SUPABASE_MCP_URL", "https://mcp.supabase.com/mcp").strip()
    root = base.split("?")[0].rstrip("/")
    params: dict[str, str] = {}
    if is_read_only():
        params["read_only"] = "true"
    org_features = os.getenv("SUPABASE_MCP_ORG_FEATURES", "").strip()
    if org_features:
        params["features"] = org_features
    if not params:
        return root
    return f"{root}?{urlencode(params)}"


def missing_project_ref_message() -> str:
    return (
        "尚未选择 Supabase 项目。请在前端完成 OAuth 授权后，"
        "从项目列表中选择要连接的数据库；"
        "或在服务器 .env 设置 SUPABASE_PROJECT_REF=项目ID。"
    )
