"""
analysisNode 之后的条件路由。

三路分流（见 route_after_analysis）：
- generation        → 完整代码生成（CREATE / MODIFY 等）
- database_inquiry  → QA 且需要联库，先走 Supabase 子图再 SQL 探查
- conversational    → 纯闲聊 / 无需联库的 QA，直接 chatReplyNode
"""
from typing import Literal

from agents.utils.supabase_integration import needs_database_connection


def _normalize_intent_type(analysis: dict) -> str:
    raw = analysis.get("type", "")
    if isinstance(raw, dict):
        raw = raw.get("value", "")
    return str(raw or "").upper().replace("INTENTTYPE.", "")


def route_after_analysis(state: dict) -> Literal["generation", "database_inquiry", "conversational"]:
    """根据 analysis.type 与 needsDatabase 决定下一跳节点。"""
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
