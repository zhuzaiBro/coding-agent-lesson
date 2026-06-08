"""Figma MCP — 浏览器 OAuth 授权（与 Supabase 一致）。"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from pydantic import BaseModel, Field

from config.figma import (
    FIGMA_OAUTH_CONFIG_COOKIE,
    FIGMA_OAUTH_COOKIE,
    get_frontend_origin,
    get_mcp_mode,
    get_mcp_url,
    get_oauth_redirect_uri,
    is_figma_configured,
)
from services.figma.mcp_client import get_figma_mcp_client, reset_figma_mcp_client
from services.figma.oauth_flow import (
    clear_session,
    clear_user_oauth_client,
    complete_authorization,
    set_user_oauth_client,
    start_authorization,
)


class FigmaOAuthConfigBody(BaseModel):
    client_id: str = Field(description="Figma OAuth Client ID")
    client_secret: str = Field(description="Figma OAuth Client Secret")

router = APIRouter()

FIGMA_REMOTE_DOCS = (
    "https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/"
)


@router.get("/oauth/config")
async def figma_oauth_config_info(request: Request):
    """供前端 Dialog 展示回调地址与文档链接。"""
    has_config = bool(request.cookies.get(FIGMA_OAUTH_CONFIG_COOKIE))
    return {
        "redirectUri": get_oauth_redirect_uri(),
        "docsUrl": FIGMA_REMOTE_DOCS,
        "hasStoredConfig": has_config,
    }


@router.post("/oauth/config")
async def figma_oauth_config_save(body: FigmaOAuthConfigBody):
    """保存用户在前端 Dialog 输入的 OAuth 客户端凭证（仅服务端 session，不入库）。"""
    if not body.client_id.strip() or not body.client_secret.strip():
        raise HTTPException(status_code=400, detail="请填写 Client ID 与 Client Secret")

    import secrets as _secrets

    config_sid = _secrets.token_urlsafe(16)
    set_user_oauth_client(config_sid, body.client_id, body.client_secret)
    response = JSONResponse(
        {
            "ok": True,
            "redirectUri": get_oauth_redirect_uri(),
        }
    )
    response.set_cookie(
        key=FIGMA_OAUTH_CONFIG_COOKIE,
        value=config_sid,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return response


def _oauth_start_response(request: Request):
    """生成授权 URL 并设置 session cookie。"""
    config_sid = request.cookies.get(FIGMA_OAUTH_CONFIG_COOKIE)
    authorize_url, session_id = start_authorization(config_sid)
    response = JSONResponse(
        {
            "authorizeUrl": authorize_url,
            "mode": "remote",
            "mcpUrl": get_mcp_url(),
            "docsUrl": FIGMA_REMOTE_DOCS,
        }
    )
    response.set_cookie(
        key=FIGMA_OAUTH_COOKIE,
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return response


@router.get("/oauth/start")
async def figma_oauth_start(request: Request):
    """返回 Figma MCP OAuth 授权页 URL，前端 window.open 打开。"""
    if get_mcp_mode() == "desktop":
        raise HTTPException(
            status_code=400,
            detail="当前为 desktop 模式，请设置 FIGMA_MCP_MODE=remote 使用网页 OAuth",
        )
    try:
        return _oauth_start_response(request)
    except RuntimeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/connect/start")
async def figma_connect_start(request: Request):
    """兼容旧路径，等同 /oauth/start。"""
    return await figma_oauth_start(request)


@router.get("/oauth/callback")
async def figma_oauth_callback(
    code: str = "",
    state: str = "",
    error: str = "",
):
    frontend = get_frontend_origin()
    if error:
        return RedirectResponse(f"{frontend}/auth/figma/callback?error={error}")
    if not code or not state:
        return RedirectResponse(f"{frontend}/auth/figma/callback?error=missing_code")

    session_id = complete_authorization(code, state)
    if not session_id:
        return RedirectResponse(f"{frontend}/auth/figma/callback?error=invalid_state")

    response = RedirectResponse(f"{frontend}/auth/figma/callback?success=1")
    response.set_cookie(
        key=FIGMA_OAUTH_COOKIE,
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return response


@router.post("/oauth/logout")
async def figma_oauth_logout(request: Request):
    session_id = request.cookies.get(FIGMA_OAUTH_COOKIE)
    config_sid = request.cookies.get(FIGMA_OAUTH_CONFIG_COOKIE)
    clear_session(session_id)
    clear_user_oauth_client(config_sid)
    reset_figma_mcp_client()
    response = JSONResponse({"ok": True})
    response.delete_cookie(FIGMA_OAUTH_COOKIE)
    response.delete_cookie(FIGMA_OAUTH_CONFIG_COOKIE)
    return response


@router.get("/status")
async def figma_status():
    base = {
        "mode": get_mcp_mode(),
        "mcpUrl": get_mcp_url(),
        "configured": is_figma_configured(),
        "docsUrl": FIGMA_REMOTE_DOCS,
        "authMethod": "oauth",
    }
    if not is_figma_configured():
        return {
            **base,
            "ok": False,
            "message": "请点击 Figma 在浏览器完成 OAuth 授权",
        }
    try:
        client = get_figma_mcp_client()
        ping = await client.ping()
        return {**base, **ping}
    except Exception as error:
        reset_figma_mcp_client()
        return {**base, "ok": False, "message": str(error)}
