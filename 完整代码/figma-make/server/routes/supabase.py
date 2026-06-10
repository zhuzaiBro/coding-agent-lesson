"""Supabase MCP proxy routes for health checks and schema introspection."""
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from config.supabase import (
    build_mcp_url,
    get_project_ref,
    has_project_ref,
    is_read_only,
    is_supabase_configured,
    missing_project_ref_message,
)
from config.supabase import OAUTH_COOKIE
from services.supabase.mcp_client import get_supabase_mcp_client, reset_supabase_mcp_client
from config.app_urls import get_frontend_origin, get_supabase_oauth_redirect_uri
from services.supabase.oauth_flow import (
    clear_session,
    complete_authorization,
    get_access_token_for_session,
    get_session_project,
    resolve_frontend_origin,
    set_session_project,
    start_authorization,
)
from services.supabase.project_list import fetch_accessible_projects

router = APIRouter()


class SqlRequest(BaseModel):
    query: str = Field(description="SQL via MCP execute_sql")


class MigrationRequest(BaseModel):
    name: str = Field(description="Migration name, e.g. add_todos_table")
    query: str = Field(description="DDL SQL for apply_migration")


class SelectProjectBody(BaseModel):
    projectRef: str = Field(description="Supabase project ref / ID")
    projectName: str = Field(default="", description="可选展示名")


@router.get("/oauth/config")
async def supabase_oauth_config_info():
    """供前端展示当前 OAuth 回调地址（排查 localhost 误配）。"""
    return {
        "redirectUri": get_supabase_oauth_redirect_uri(),
        "frontendOrigin": get_frontend_origin(),
        "docsUrl": "https://supabase.com/docs/guides/ai-tools/mcp",
    }


@router.get("/oauth/start")
async def supabase_oauth_start(request: Request):
    """返回 Supabase 官方 OAuth 授权页 URL，并在浏览器中打开即可完成授权。"""
    frontend_origin = (
        request.headers.get("x-frontend-origin")
        or request.headers.get("origin")
        or ""
    ).strip()
    authorize_url, session_id = start_authorization(frontend_origin=frontend_origin)
    response = JSONResponse({"authorizeUrl": authorize_url})
    response.set_cookie(
        key=OAUTH_COOKIE,
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return response


@router.get("/oauth/callback")
async def supabase_oauth_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
):
    """Supabase OAuth 回调；成功后跳回前端。"""
    if error:
        frontend = get_frontend_origin()
        return RedirectResponse(
            f"{frontend}/auth/supabase/callback?error={error}"
        )
    if not code or not state:
        return RedirectResponse(
            f"{get_frontend_origin()}/auth/supabase/callback?error=missing_code"
        )

    session_id = complete_authorization(code, state)
    frontend = resolve_frontend_origin(session_id)
    if not session_id:
        return RedirectResponse(
            f"{frontend}/auth/supabase/callback?error=invalid_state"
        )

    # 仅一个可访问项目时自动写入 session，无需前端弹窗或改 .env
    env_ref = os.getenv("SUPABASE_PROJECT_REF", "").strip()
    if not env_ref and not get_session_project(session_id):
        token = get_access_token_for_session(session_id)
        if token:
            try:
                projects = await fetch_accessible_projects(token)
                if len(projects) == 1:
                    set_session_project(
                        session_id,
                        projects[0]["ref"],
                        projects[0].get("name", ""),
                    )
                    reset_supabase_mcp_client()
            except Exception as err:
                print(f"[Supabase OAuth] 单项目自动绑定失败: {err}")

    response = RedirectResponse(f"{frontend}/auth/supabase/callback?success=1")
    response.set_cookie(
        key=OAUTH_COOKIE,
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return response


@router.post("/oauth/logout")
async def supabase_oauth_logout(request: Request):
    session_id = request.cookies.get(OAUTH_COOKIE)
    clear_session(session_id)
    reset_supabase_mcp_client()
    response = JSONResponse({"ok": True})
    response.delete_cookie(OAUTH_COOKIE)
    return response


@router.get("/oauth/projects")
async def supabase_oauth_projects(request: Request):
    """授权完成后列出当前账号可访问的 Supabase 项目。"""
    session_id = request.cookies.get(OAUTH_COOKIE)
    token = get_access_token_for_session(session_id)
    if not token:
        raise HTTPException(status_code=401, detail="请先完成 Supabase OAuth 授权")

    env_ref = os.getenv("SUPABASE_PROJECT_REF", "").strip()
    if env_ref:
        return {
            "projects": [
                {"ref": env_ref, "name": env_ref, "source": "env"},
            ],
        }

    try:
        projects = await fetch_accessible_projects(token)
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"无法获取项目列表: {error}",
        ) from error

    if not projects:
        raise HTTPException(
            status_code=404,
            detail="该账号下未找到可访问的 Supabase 项目",
        )
    return {"projects": projects}


@router.get("/oauth/project")
async def supabase_oauth_project(request: Request):
    """当前 OAuth 会话是否已选择项目。"""
    session_id = request.cookies.get(OAUTH_COOKIE)
    env_ref = os.getenv("SUPABASE_PROJECT_REF", "").strip()
    if env_ref:
        return {
            "selected": {"ref": env_ref, "name": env_ref, "source": "env"},
            "needsSelection": False,
        }

    selected = get_session_project(session_id)
    has_token = bool(get_access_token_for_session(session_id))
    return {
        "selected": selected,
        "needsSelection": has_token and not selected,
    }


@router.post("/oauth/project")
async def supabase_oauth_select_project(request: Request, body: SelectProjectBody):
    """将用户选择的项目写入 OAuth 会话（无需改服务器 .env）。"""
    session_id = request.cookies.get(OAUTH_COOKIE)
    if not session_id or not get_access_token_for_session(session_id):
        raise HTTPException(status_code=401, detail="请先完成 OAuth 授权")

    ref = body.projectRef.strip()
    if not ref:
        raise HTTPException(status_code=400, detail="projectRef 不能为空")

    set_session_project(session_id, ref, body.projectName)
    reset_supabase_mcp_client()
    name = (body.projectName or ref).strip() or ref
    return {"ok": True, "projectRef": ref, "projectName": name}


def _mcp_database_capabilities() -> dict:
    """当前进程可用的数据库相关 MCP 工具说明。"""
    read_only = is_read_only()
    tools = ["list_tables", "list_migrations", "get_project_url", "get_publishable_keys"]
    if read_only:
        tools.append("execute_sql (SELECT only via read_only Postgres role)")
    else:
        tools.extend(
            [
                "execute_sql (DML/DDL)",
                "apply_migration (CREATE/ALTER TABLE, etc.)",
                "generate_typescript_types",
            ]
        )
    return {
        "readOnly": read_only,
        "canEditSchema": not read_only,
        "canExecuteWriteSql": not read_only,
        "tools": tools,
    }


@router.get("/status")
async def supabase_status():
    """Check whether Supabase MCP is configured and reachable."""
    caps = _mcp_database_capabilities()
    if not is_supabase_configured():
        return {
            "configured": False,
            "authMethod": "oauth",
            "message": "请点击「Supabase」在浏览器中完成授权",
            "mcpUrl": build_mcp_url(),
            **caps,
        }
    if not has_project_ref():
        return {
            "configured": True,
            "authMethod": "oauth",
            "ok": False,
            "needsProjectRef": True,
            "needsProjectSelection": True,
            "schemaReady": False,
            "projectRef": None,
            "message": missing_project_ref_message(),
            "mcpUrl": build_mcp_url(),
            **caps,
        }
    try:
        client = get_supabase_mcp_client()
        ping = await client.ping()
        return {
            "configured": True,
            "authMethod": "oauth",
            "projectRef": ping.get("projectRef") or get_project_ref() or None,
            "needsProjectRef": not has_project_ref(),
            "needsProjectSelection": False,
            "schemaReady": ping.get("schemaReady", False),
            **ping,
            **caps,
        }
    except Exception as error:
        reset_supabase_mcp_client()
        detail = str(error)
        if "project_ref" in detail.lower() or "project_id" in detail.lower():
            detail = missing_project_ref_message()
        raise HTTPException(status_code=502, detail=detail) from error


@router.get("/schema")
async def supabase_schema(verbose: bool = True):
    """List database tables via MCP list_tables."""
    if not is_supabase_configured():
        raise HTTPException(status_code=400, detail="Supabase MCP not configured")
    try:
        client = get_supabase_mcp_client()
        text = await client.list_tables(verbose=verbose)
        return {"schema": text}
    except Exception as error:
        reset_supabase_mcp_client()
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/client-config")
async def supabase_client_config():
    """Project URL + publishable keys for frontend .env."""
    if not is_supabase_configured():
        raise HTTPException(status_code=400, detail="Supabase MCP not configured")
    try:
        client = get_supabase_mcp_client()
        return {
            "projectUrl": await client.get_project_url(),
            "publishableKeys": await client.get_publishable_keys(),
            "envExample": {
                "VITE_SUPABASE_URL": "<from projectUrl>",
                "VITE_SUPABASE_ANON_KEY": "<anon key from publishableKeys>",
            },
        }
    except Exception as error:
        reset_supabase_mcp_client()
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/migrations")
async def supabase_list_migrations():
    """List applied migrations via MCP."""
    if not is_supabase_configured():
        raise HTTPException(status_code=400, detail="Supabase MCP not configured")
    try:
        client = get_supabase_mcp_client()
        result = await client.list_migrations()
        return {"migrations": result}
    except Exception as error:
        reset_supabase_mcp_client()
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post("/migration")
async def supabase_apply_migration(body: MigrationRequest):
    """Apply DDL migration (CREATE/ALTER TABLE). Requires SUPABASE_MCP_READ_ONLY=false."""
    if is_read_only():
        raise HTTPException(
            status_code=403,
            detail="MCP is read-only. Set SUPABASE_MCP_READ_ONLY=false to edit schema.",
        )
    if not is_supabase_configured():
        raise HTTPException(status_code=400, detail="Supabase MCP not configured")
    try:
        client = get_supabase_mcp_client()
        result = await client.apply_migration(body.name, body.query)
        return {"result": result}
    except Exception as error:
        reset_supabase_mcp_client()
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post("/sql")
async def supabase_execute_sql(body: SqlRequest):
    """Execute SQL via MCP execute_sql. Writes blocked when read_only=true."""
    if not is_supabase_configured():
        raise HTTPException(status_code=400, detail="Supabase MCP not configured")
    q = body.query.strip().upper()
    if is_read_only() and any(
        q.startswith(k)
        for k in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE")
    ):
        raise HTTPException(
            status_code=403,
            detail="Write SQL blocked in read-only mode. Set SUPABASE_MCP_READ_ONLY=false.",
        )
    try:
        client = get_supabase_mcp_client()
        result = await client.execute_sql(body.query)
        return {"result": result}
    except Exception as error:
        reset_supabase_mcp_client()
        raise HTTPException(status_code=502, detail=str(error)) from error
