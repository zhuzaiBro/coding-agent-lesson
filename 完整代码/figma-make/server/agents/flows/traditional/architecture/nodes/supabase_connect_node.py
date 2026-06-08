"""Supabase subgraph: MCP connectivity check."""
from services.supabase.mcp_client import get_supabase_mcp_client


async def supabase_connect_node(state: dict) -> dict:
    if state.get("error"):
        return {}

    print("[SupabaseGraph] connectNode — checking MCP...")
    try:
        client = get_supabase_mcp_client()
        ping = await client.ping()
        project_url = str(ping.get("projectUrl") or "").strip()
        print(f"[SupabaseGraph] connectNode — ok ({project_url or 'project'})")
        return {"connected": True, "projectUrl": project_url}
    except Exception as error:
        print(f"[SupabaseGraph] connectNode — failed: {error}")
        return {"connected": False, "error": str(error)[:1000]}
