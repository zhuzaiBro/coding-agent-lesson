"""生产/本地 URL 配置（OAuth redirect、授权后跳回前端）。"""
import os
from typing import Optional

# 线上默认值（服务器 .env 未配置 API_BASE_URL 时使用，避免 OAuth 回调到 localhost）
DEFAULT_API_BASE_URL = "https://coding-agent.zood.work"
DEFAULT_FRONTEND_URL = "https://coding.zood.work"


def _is_localhost_url(url: str) -> bool:
    u = (url or "").lower()
    return "localhost" in u or "127.0.0.1" in u


def is_production_api() -> bool:
    """当前 API 是否部署在公网（非 localhost）。"""
    return not _is_localhost_url(get_api_base_url())


def normalize_frontend_origin(origin: Optional[str]) -> str:
    """
    授权完成后跳回的前端 origin。

    线上 API + 本地 dev 前端（localhost:3000 连远端 API）时，Cookie 写在 API 域下，
    localhost 无法携带该 Cookie，因此强制跳回 FRONTEND_URL（线上前端）。
    仅当 API 也是 localhost 时，才允许跳回 localhost 前端。
    """
    canonical = get_frontend_origin()
    explicit = (origin or "").strip().rstrip("/")
    if not explicit:
        return canonical
    if is_production_api() and _is_localhost_url(explicit):
        return canonical
    return explicit


def get_api_base_url() -> str:
    explicit = os.getenv("API_BASE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    # 本地开发请在 .env 显式设置 API_BASE_URL=http://localhost:7001
    return DEFAULT_API_BASE_URL


def get_frontend_origin() -> str:
    explicit = os.getenv("FRONTEND_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    return DEFAULT_FRONTEND_URL


def get_supabase_oauth_redirect_uri() -> str:
    explicit = os.getenv("SUPABASE_OAUTH_REDIRECT_URI", "").strip()
    if explicit:
        return explicit
    return f"{get_api_base_url()}/api/supabase/oauth/callback"


def get_figma_oauth_redirect_uri() -> str:
    explicit = os.getenv("FIGMA_OAUTH_REDIRECT_URI", "").strip()
    if explicit:
        return explicit
    return f"{get_api_base_url()}/api/figma/oauth/callback"
