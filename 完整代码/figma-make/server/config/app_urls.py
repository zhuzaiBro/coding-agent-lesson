"""生产/本地 URL 配置（OAuth redirect、授权后跳回前端）。"""
import os


def get_api_base_url() -> str:
    explicit = os.getenv("API_BASE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    port = os.getenv("PORT", "7001")
    return f"http://localhost:{port}"


def get_frontend_origin() -> str:
    explicit = os.getenv("FRONTEND_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    return "http://localhost:3000"


def get_supabase_oauth_redirect_uri() -> str:
    explicit = os.getenv("SUPABASE_OAUTH_REDIRECT_URI", "").strip()
    if explicit:
        return explicit
    return f"{get_api_base_url()}/api/supabase/oauth/callback"
