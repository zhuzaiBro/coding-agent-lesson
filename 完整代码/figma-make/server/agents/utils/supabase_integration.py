"""
Supabase 联库判定与提示词拼装。

needs_database_connection：决定是否调用 supabaseSubgraph、是否走 database_inquiry 分支。
format_supabase_prompt_block：将 MCP 拉取的 schema/types 格式化为 LLM 系统提示片段。
"""
from typing import Any, Dict, Optional

from config.supabase import is_supabase_configured


def needs_database_connection(state: dict) -> bool:
    """
    本请求是否需要连接 Supabase MCP（优先级从高到低）：
    未配置 → 用户显式关闭 → 用户显式开启 → LLM 判断 → state 兜底。
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
    """向后兼容别名。"""
    return needs_database_connection(state)


def _normalize_intent_type(analysis: dict) -> str:
    raw = analysis.get("type", "")
    if isinstance(raw, dict):
        raw = raw.get("value", "")
    return str(raw or "").upper().replace("INTENTTYPE.", "")


def is_database_inquiry(state: dict) -> bool:
    """QA 且需要联库 → 走问询分支（非代码生成）。"""
    analysis = state.get("analysis") or {}
    return _normalize_intent_type(analysis) == "QA" and needs_database_connection(state)


def format_supabase_prompt_block(supabase: Optional[Dict[str, Any]]) -> str:
    if not supabase or not supabase.get("enabled"):
        return ""

    parts = [
        "\n【Supabase 后端 — 使用真实项目连接，不要 Mock 数据库】\n",
        f"- 项目 URL: {supabase.get('projectUrl', '(见 MCP)')}\n",
    ]
    if supabase.get("publishableKey"):
        parts.append(
            "- 生成代码中使用环境变量 VITE_SUPABASE_URL 与 VITE_SUPABASE_ANON_KEY "
            "（切勿在源码中硬编码密钥）。\n"
        )
    if supabase.get("schemaSummary"):
        parts.append("\n### 数据库 Schema（来自 Supabase MCP）\n")
        parts.append(str(supabase["schemaSummary"])[:12000])
        parts.append("\n")
    if supabase.get("typescriptTypes"):
        parts.append("\n### 生成的 DB 类型（放在 /types/database.ts）\n")
        parts.append(str(supabase["typescriptTypes"])[:8000])
        parts.append("\n")
    parts.append(
        "- 客户端使用 @supabase/supabase-js；表名/列名须与上方 schema 一致。\n"
        "- 采用 RLS 安全写法；除非用户明确要求，不得虚构未列出的表。\n"
    )
    if supabase.get("readOnly") is False:
        parts.append(
            "- 后端 MCP 可在用户明确要求新表/列时通过 apply_migration / execute_sql 修改 schema；"
            "生成应用代码须与最终 schema 一致。\n"
        )
    else:
        parts.append(
            "- 数据库 MCP 为只读：代码中仅查询已有表，勿假设服务端会 CREATE TABLE，"
            "除非用户将手动执行迁移。\n"
        )
    return "".join(parts)
