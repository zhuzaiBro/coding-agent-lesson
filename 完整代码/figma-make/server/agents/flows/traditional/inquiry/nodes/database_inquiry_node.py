"""
数据库问询节点（QA + 需要联库时分支）。

多轮循环（最多 6 轮）：LLM 生成 SQL → Supabase MCP execute_sql → 结果回填 → 直至产出最终回答。
仅允许只读 SQL（is_read_only_sql 校验），结果写入 state.inquiry 供 chatReplyNode 展示。
"""
import json
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from agents.adapters.route_helpers import get_last_text
from agents.flows.traditional.inquiry.prompts.inquiry_prompts import INQUIRY_SYSTEM_PROMPT
from agents.flows.traditional.inquiry.schemas.inquiry_schema import InquiryStep
from agents.utils.mock import try_execute_mock
from agents.utils.model import get_structured_model
from agents.utils.sql_guard import is_read_only_sql
from config.supabase import is_supabase_configured
from services.supabase.mcp_client import get_supabase_mcp_client

MAX_INQUIRY_ROUNDS = 6
_RESULT_PREVIEW_CHARS = 6000


async def database_inquiry_node(state: dict) -> dict:
    """Run read-only SQL loop until LLM produces a final answer."""
    mock_result = await try_execute_mock(
        state,
        "inquiryNode",
        "inquiryResult.json",
        lambda data, _state: {"inquiry": data.get("inquiry") or data},
    )
    if mock_result:
        return mock_result

    print("--- DatabaseInquiryNode Start ---")

    user_question = get_last_text(state.get("messages", []))
    analysis = state.get("analysis") or {}
    supabase = state.get("supabase") or {}
    schema_summary = supabase.get("schemaSummary") or ""
    db_error = supabase.get("error") or ""

    if not is_supabase_configured():
        payload = _error_inquiry(
            user_question,
            "Supabase 未连接。请在前端点击 Supabase 完成 OAuth 授权后再提问。",
        )
        print("--- DatabaseInquiryNode End (not configured) ---")
        return {"inquiry": payload}

    if supabase.get("enabled") is False and db_error:
        payload = _error_inquiry(
            user_question,
            f"Supabase MCP 连接失败：{db_error}",
        )
        print("--- DatabaseInquiryNode End (mcp error) ---")
        return {"inquiry": payload}

    model = get_structured_model(InquiryStep)
    trace: List[Dict[str, Any]] = []
    prior_results: List[str] = []

    for round_idx in range(1, MAX_INQUIRY_ROUNDS + 1):
        context_block = _build_context(
            user_question=user_question,
            analysis=analysis,
            schema_summary=schema_summary,
            prior_results=prior_results,
            round_idx=round_idx,
        )
        prompt = [
            SystemMessage(content=INQUIRY_SYSTEM_PROMPT),
            HumanMessage(content=context_block),
        ]

        try:
            step = await model.ainvoke(prompt)
            step_dict = step.model_dump() if hasattr(step, "model_dump") else step
        except Exception as error:
            print(f"[DatabaseInquiry] LLM round {round_idx} failed: {error}")
            payload = _error_inquiry(user_question, f"分析失败：{error}")
            return {"inquiry": payload}

        action = _normalize_action(step_dict.get("action"))
        message = str(step_dict.get("message") or "").strip()

        if action == "answer":
            print(f"[DatabaseInquiry] Answered after {round_idx} round(s), {len(trace)} queries")
            print("--- DatabaseInquiryNode End ---")
            return {
                "inquiry": {
                    "status": "ok",
                    "question": user_question,
                    "message": message or "已完成数据库探查，但未生成文字结论。",
                    "trace": trace,
                    "rounds": round_idx,
                }
            }

        sql = str(step_dict.get("sql") or "").strip()
        if not sql:
            prior_results.append(f"Round {round_idx}: model requested query but sql was empty.")
            continue

        if not is_read_only_sql(sql):
            prior_results.append(
                f"Round {round_idx}: rejected non-read-only SQL.\nReason: {message}"
            )
            trace.append({
                "round": round_idx,
                "sql": sql,
                "status": "rejected",
                "reason": "仅允许 SELECT/WITH 只读查询",
            })
            continue

        print(f"[DatabaseInquiry] Round {round_idx} SQL: {sql[:120]}...")
        try:
            client = get_supabase_mcp_client()
            raw_result = await client.execute_sql(sql)
            preview = raw_result[:_RESULT_PREVIEW_CHARS]
            trace.append({
                "round": round_idx,
                "sql": sql,
                "status": "ok",
                "resultPreview": preview,
                "truncated": len(raw_result) > _RESULT_PREVIEW_CHARS,
            })
            prior_results.append(
                f"### Query round {round_idx}\nSQL:\n{sql}\n\nResult:\n{preview}"
            )
        except Exception as error:
            err_text = str(error)[:800]
            trace.append({
                "round": round_idx,
                "sql": sql,
                "status": "error",
                "error": err_text,
            })
            prior_results.append(
                f"### Query round {round_idx} FAILED\nSQL:\n{sql}\n\nError:\n{err_text}"
            )

    print(f"[DatabaseInquiry] Max rounds ({MAX_INQUIRY_ROUNDS}) reached")
    print("--- DatabaseInquiryNode End ---")
    return {
        "inquiry": {
            "status": "max_rounds",
            "question": user_question,
            "message": (
                "已执行多轮数据库查询仍未得到完整结论。"
                "请查看下方 SQL 探查记录，或缩小问题范围后重试。"
            ),
            "trace": trace,
            "rounds": MAX_INQUIRY_ROUNDS,
        }
    }


def _build_context(
    *,
    user_question: str,
    analysis: dict,
    schema_summary: str,
    prior_results: List[str],
    round_idx: int,
) -> str:
    parts = [
        f"User question:\n{user_question}\n",
        f"Analysis summary: {analysis.get('summary', '')}\n",
        f"Database reason: {analysis.get('databaseReason', '')}\n",
        f"Round: {round_idx}/{MAX_INQUIRY_ROUNDS}\n",
    ]
    if schema_summary:
        parts.append(f"\n### Schema (from MCP)\n{schema_summary[:10000]}\n")
    else:
        parts.append("\n### Schema\n(not available — infer carefully from query errors)\n")
    if prior_results:
        parts.append("\n### Prior query results\n")
        parts.append("\n\n".join(prior_results[-4:]))
    parts.append("\nOutput the next InquiryStep JSON.")
    return "".join(parts)


def _error_inquiry(question: str, message: str) -> Dict[str, Any]:
    return {
        "status": "error",
        "question": question,
        "message": message,
        "trace": [],
        "rounds": 0,
    }


def _normalize_action(raw: Any) -> str:
    if raw is None:
        return ""
    if hasattr(raw, "value"):
        return str(raw.value).lower()
    text = str(raw).lower()
    if "." in text:
        text = text.split(".")[-1]
    return text
