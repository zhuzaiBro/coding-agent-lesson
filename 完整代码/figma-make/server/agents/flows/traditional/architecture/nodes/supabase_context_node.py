"""Deprecated: use agents.graphs.supabase_graph via traditional_graph.run_supabase_graph."""
from agents.graphs.supabase_graph import supabase_graph
from agents.utils.supabase_integration import request_wants_supabase


async def supabase_context_node(state: dict) -> dict:
    """Backward-compatible wrapper around the Supabase subgraph."""
    if not request_wants_supabase(state):
        return {}
    result = await supabase_graph.ainvoke({
        "useSupabase": state.get("useSupabase"),
        "messages": state.get("messages"),
    })
    return {"supabase": result.get("supabase", {})}
