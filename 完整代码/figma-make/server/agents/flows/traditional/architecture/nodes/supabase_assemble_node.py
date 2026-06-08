"""Supabase subgraph: merge MCP results into state.supabase payload."""
from config.supabase import is_read_only


async def supabase_assemble_node(state: dict) -> dict:
    error = state.get("error")
    if error:
        print(f"[SupabaseGraph] assembleNode — error payload: {error[:120]}")
        return {
            "supabase": {
                "enabled": False,
                "error": error,
            }
        }

    payload = {
        "enabled": True,
        "projectUrl": state.get("projectUrl", ""),
        "publishableKeyHint": state.get("publishableKeyHint", False),
        "schemaSummary": state.get("schemaSummary", ""),
        "typescriptTypes": state.get("typescriptTypes", ""),
        "readOnly": is_read_only(),
    }

    print(
        f"[SupabaseGraph] assembleNode — {payload['projectUrl'] or 'project'} "
        f"({len(payload['schemaSummary'])} schema chars)"
    )
    return {"supabase": payload}
