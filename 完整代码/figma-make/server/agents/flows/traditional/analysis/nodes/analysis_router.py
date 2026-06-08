"""Route traditional flow after analysisNode."""
from typing import Literal

from agents.utils.supabase_integration import needs_database_connection


def _normalize_intent_type(analysis: dict) -> str:
    raw = analysis.get("type", "")
    if isinstance(raw, dict):
        raw = raw.get("value", "")
    return str(raw or "").upper().replace("INTENTTYPE.", "")


def route_after_analysis(state: dict) -> Literal["generation", "database_inquiry", "conversational"]:
    """
    - QA + needsDatabase → database inquiry (Supabase MCP + execute_sql)
    - QA / CHIT_CHAT without DB → conversational chatReply
    - CREATE / MODIFY → full code generation pipeline
    """
    analysis = state.get("analysis") or {}
    intent_type = _normalize_intent_type(analysis)

    if intent_type == "QA" and needs_database_connection(state):
        print("[Route] database_inquiry — QA requires live database")
        return "database_inquiry"

    if intent_type in ("QA", "CHIT_CHAT"):
        print(f"[Route] conversational — {intent_type}")
        return "conversational"

    print(f"[Route] generation — {intent_type or 'CREATE'}")
    return "generation"
