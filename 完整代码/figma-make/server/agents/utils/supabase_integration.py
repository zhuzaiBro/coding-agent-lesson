"""Detect Supabase / live database need and format MCP context for LLM prompts."""
from typing import Any, Dict, Optional

from config.supabase import is_supabase_configured


def needs_database_connection(state: dict) -> bool:
    """
    Whether the pipeline should connect Supabase MCP.

    Priority (high → low):
      1. Supabase not configured → False
      2. User explicit opt-out (useSupabase=False) → False
      3. User explicit opt-in (useSupabase=True) → True
      4. LLM analysis.needsDatabase → True/False
      5. Fallback state.needsDatabase → True/False
    """
    if not is_supabase_configured():
        return False

    explicit = state.get("useSupabase")
    if explicit is False:
        return False
    if explicit is True:
        return True

    analysis = state.get("analysis") or {}
    if "needsDatabase" in analysis:
        return bool(analysis.get("needsDatabase"))

    if "needsDatabase" in state:
        return bool(state.get("needsDatabase"))

    return False


def request_wants_supabase(state: dict) -> bool:
    """Backward-compatible alias."""
    return needs_database_connection(state)


def _normalize_intent_type(analysis: dict) -> str:
    raw = analysis.get("type", "")
    if isinstance(raw, dict):
        raw = raw.get("value", "")
    return str(raw or "").upper().replace("INTENTTYPE.", "")


def is_database_inquiry(state: dict) -> bool:
    """QA + needs live database → inquiry branch (not code generation)."""
    analysis = state.get("analysis") or {}
    return _normalize_intent_type(analysis) == "QA" and needs_database_connection(state)


def format_supabase_prompt_block(supabase: Optional[Dict[str, Any]]) -> str:
    if not supabase or not supabase.get("enabled"):
        return ""

    parts = [
        "\n【Supabase backend — use real project connection, do not mock DB】\n",
        f"- Project URL: {supabase.get('projectUrl', '(see MCP)')}\n",
    ]
    if supabase.get("publishableKey"):
        parts.append(
            "- Use env vars VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in generated code "
            "(never hardcode secrets in source).\n"
        )
    if supabase.get("schemaSummary"):
        parts.append("\n### Database schema (from Supabase MCP)\n")
        parts.append(str(supabase["schemaSummary"])[:12000])
        parts.append("\n")
    if supabase.get("typescriptTypes"):
        parts.append("\n### Generated DB types (place at /types/database.ts)\n")
        parts.append(str(supabase["typescriptTypes"])[:8000])
        parts.append("\n")
    parts.append(
        "- Use @supabase/supabase-js for client; align table/column names with schema above.\n"
        "- Enable RLS-safe patterns; do not invent tables not listed unless user explicitly asks.\n"
    )
    if supabase.get("readOnly") is False:
        parts.append(
            "- Backend MCP can apply_migration / execute_sql to edit schema when user explicitly "
            "requests new tables or columns; generated app code should match resulting schema.\n"
        )
    else:
        parts.append(
            "- Database MCP is read-only: only query existing tables in code, do not assume "
            "server will CREATE TABLE unless user will run migrations manually.\n"
        )
    return "".join(parts)
