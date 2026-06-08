"""Supabase subgraph: project URL and publishable keys."""
from agents.utils.supabase_mcp_helpers import parse_publishable_anon_key
from services.supabase.mcp_client import get_supabase_mcp_client


async def supabase_fetch_config_node(state: dict) -> dict:
    if state.get("error"):
        return {}

    print("[SupabaseGraph] fetchConfigNode...")
    try:
        client = get_supabase_mcp_client()
        project_url = (await client.get_project_url()).strip() or state.get("projectUrl", "")
        keys_raw = await client.get_publishable_keys()
        anon_key = parse_publishable_anon_key(keys_raw)
        print(f"[SupabaseGraph] fetchConfigNode — url={project_url or '(empty)'}")
        return {
            "projectUrl": project_url,
            "publishableKeyHint": bool(anon_key),
        }
    except Exception as error:
        print(f"[SupabaseGraph] fetchConfigNode — failed: {error}")
        return {"error": str(error)[:1000]}
