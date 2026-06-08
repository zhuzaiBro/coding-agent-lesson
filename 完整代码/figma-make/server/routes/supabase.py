"""Supabase MCP proxy routes for health checks and schema introspection."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from config.supabase import build_mcp_url, is_read_only, is_supabase_configured
from config.supabase import OAUTH_COOKIE
from services.supabase.mcp_client import get_supabase_mcp_client, reset_supabase_mcp_client
from services.supabase.oauth_flow import (
    clear_session,
    complete_authorization,
    get_frontend_origin,
    get_oauth_redirect_uri,
    start_authorization,
)

router = APIRouter()


class SqlRequest(BaseModel):
    query: str = Field(description="SQL via MCP execute_sql")


class MigrationRequest(BaseModel):
    name: str = Field(description="Migration name, e.g. add_todos_table")
    query: str = Field(description="DDL SQL for apply_migration")


@router.get("/oauth/start")
async def supabase_oauth_start():
    """返回 Supabase 官方 OAuth 授权页 URL，并在浏览器中打开即可完成授权。"""
    authorize_url, session_id = start_authorization()
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
    frontend = get_frontend_origin()
    if error:
        return RedirectResponse(
            f"{frontend}/auth/supabase/callback?error={error}"
        )
    if not code or not state:
        return RedirectResponse(
            f"{frontend}/auth/supabase/callback?error=missing_code"
        )

    session_id = complete_authorization(code, state)
    if not session_id:
        return RedirectResponse(
            f"{frontend}/auth/supabase/callback?error=invalid_state"
        )

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
    try:
        client = get_supabase_mcp_client()
        ping = await client.ping()
        return {"configured": True, **ping, **caps}
    except Exception as error:
        reset_supabase_mcp_client()
        raise HTTPException(status_code=502, detail=str(error)) from error


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
