"""Supabase subgraph: generate TypeScript types (skipped when read-only)."""
from config.supabase import is_read_only
from services.supabase.mcp_client import get_supabase_mcp_client


async def supabase_fetch_types_node(state: dict) -> dict:
    if state.get("error"):
        return {}

    if is_read_only():
        print("[SupabaseGraph] fetchTypesNode — skipped (read_only MCP)")
        return {"typescriptTypes": ""}

    print("[SupabaseGraph] fetchTypesNode...")
    try:
        client = get_supabase_mcp_client()
        typescript_types = await client.generate_typescript_types()
        print(f"[SupabaseGraph] fetchTypesNode — {len(typescript_types)} chars")
        return {"typescriptTypes": typescript_types}
    except Exception as error:
        print(f"[SupabaseGraph] fetchTypesNode — skipped: {error}")
        return {"typescriptTypes": ""}
