"""Figma Remote MCP（默认 OAuth + https://mcp.figma.com/mcp）。"""
from contextvars import ContextVar
import os
from typing import Literal, Optional

FigmaMcpMode = Literal["desktop", "remote"]

_request_figma_access_token: ContextVar[Optional[str]] = ContextVar(
    "figma_oauth_access_token", default=None
)

FIGMA_OAUTH_COOKIE = "zood_figma_sid"
FIGMA_OAUTH_CONFIG_COOKIE = "zood_figma_cfg"


def set_request_figma_oauth_token(token: Optional[str]) -> None:
    _request_figma_access_token.set(token)


def get_mcp_mode() -> FigmaMcpMode:
    mode = os.getenv("FIGMA_MCP_MODE", "remote").strip().lower()
    return "desktop" if mode == "desktop" else "remote"


def get_mcp_url() -> str:
    explicit = os.getenv("FIGMA_MCP_URL", "").strip()
    if explicit:
        return explicit
    if get_mcp_mode() == "remote":
        return "https://mcp.figma.com/mcp"
    return "http://127.0.0.1:3845/mcp"


def get_frontend_origin() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def get_oauth_redirect_uri() -> str:
    explicit = os.getenv("FIGMA_OAUTH_REDIRECT_URI", "").strip()
    if explicit:
        return explicit
    port = os.getenv("PORT", "7001")
    return f"http://localhost:{port}/api/figma/oauth/callback"


def get_access_token() -> str:
    oauth = _request_figma_access_token.get()
    if oauth:
        return oauth
    return (
        os.getenv("FIGMA_ACCESS_TOKEN", "").strip()
        or os.getenv("FIGMA_API_KEY", "").strip()
    )


def is_figma_configured() -> bool:
    if get_mcp_mode() == "desktop":
        return True
    return bool(get_access_token())


def get_figma_setup_steps() -> list[str]:
    return [
        "点击「Figma」打开浏览器授权页",
        "登录 Figma 并允许 MCP 访问",
        "授权完成后自动回到本应用",
        "在对话中粘贴 Figma 设计链接即可生成代码",
    ]
