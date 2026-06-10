"""生产/本地 URL 配置（OAuth redirect、授权后跳回前端）。"""
import os

# 线上默认值（服务器 .env 未配置 API_BASE_URL 时使用，避免 OAuth 回调到 localhost）
DEFAULT_API_BASE_URL = "https://coding-agent.zood.work"
DEFAULT_FRONTEND_URL = "https://coding.zood.work"


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
