"""Supabase subgraph: list database tables via MCP."""
from services.supabase.mcp_client import get_supabase_mcp_client


async def supabase_fetch_schema_node(state: dict) -> dict:
    if state.get("error"):
        return {}

    print("[SupabaseGraph] fetchSchemaNode...")
    try:
        client = get_supabase_mcp_client()
        schema_summary = await client.list_tables(verbose=True)
        print(f"[SupabaseGraph] fetchSchemaNode — {len(schema_summary)} chars")
        return {"schemaSummary": schema_summary}
    except Exception as error:
        print(f"[SupabaseGraph] fetchSchemaNode — failed: {error}")
        return {"error": str(error)[:1000]}
