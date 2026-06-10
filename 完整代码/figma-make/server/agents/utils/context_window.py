"""
对话上下文窗口管理：估算 token 占用，超限时 LLM 压缩历史为摘要。

策略：
- 保留最近 N 条原始消息（默认 8）
- 更早消息合并进 conversationSummary（与 checkpoint 中已有摘要合并）
- 返回裁剪后的 messages + 更新后的 summary，供 chat 路由与各节点使用
"""
from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from agents.utils.model import get_model
from config.context import (
    get_context_keep_recent_messages,
    get_context_max_tokens,
    get_context_summary_max_chars,
    is_context_compression_enabled,
)

_SUMMARY_SYSTEM_PROMPT = """你是代码生成 Agent 的对话记忆压缩器。
将较早的对话合并为简洁中文摘要，供后续多轮修改时保留关键上下文。

必须保留：
- 用户目标、产品类型、核心功能
- 已做过的修改请求与结果倾向
- 技术约束（Supabase/Figma/样式/布局等）
- 提到的表名、API、组件名、文件路径
- 尚未解决的问题

输出纯文本摘要（可用短列表），不要 JSON，不要寒暄。"""


def _message_content(msg: Any) -> str:
    if isinstance(msg, dict):
        content = msg.get("content", "")
    else:
        content = getattr(msg, "content", "")
    if not isinstance(content, str):
        return ""
    return content.strip()


def _message_role(msg: Any) -> str:
    if isinstance(msg, dict):
        role = msg.get("role", "user")
    else:
        role = getattr(msg, "role", "user")
    return str(role or "user")


def estimate_messages_tokens(messages: List[Any]) -> int:
    """粗略 token 估算（字符数 / 4）。"""
    total_chars = 0
    for msg in messages or []:
        text = _message_content(msg)
        if not text:
            continue
        total_chars += len(text) + len(_message_role(msg)) + 8
    return max(0, total_chars // 4)


def estimate_summary_tokens(summary: str) -> int:
    text = (summary or "").strip()
    if not text:
        return 0
    return max(1, len(text) // 4)


def estimate_context_tokens(messages: List[Any], summary: str = "") -> int:
    return estimate_messages_tokens(messages) + estimate_summary_tokens(summary)


def format_summary_block(summary: str) -> str:
    text = (summary or "").strip()
    if not text:
        return ""
    return f"## 历史对话摘要\n{text}\n"


async def _summarize_segment(
    segment: List[Any],
    previous_summary: str = "",
) -> str:
    if not segment and not previous_summary:
        return ""

    lines: List[str] = []
    for msg in segment:
        role = _message_role(msg)
        content = _message_content(msg)
        if not content:
            continue
        clipped = content if len(content) <= 2500 else content[:2500] + "…"
        lines.append(f"{role}: {clipped}")

    if not lines and previous_summary:
        return previous_summary.strip()

    human = []
    if previous_summary.strip():
        human.append("已有摘要（请合并去重，不要重复罗列）：\n")
        human.append(previous_summary.strip())
        human.append("\n\n")
    human.append("待压缩的新消息：\n")
    human.append("\n".join(lines))

    model = get_model()
    response = await model.ainvoke(
        [
            SystemMessage(content=_SUMMARY_SYSTEM_PROMPT),
            HumanMessage(content="".join(human)),
        ]
    )
    text = getattr(response, "content", "") or ""
    if not isinstance(text, str):
        text = str(text)
    text = text.strip()
    max_chars = get_context_summary_max_chars()
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "…"
    return text


def _serialize_messages_for_client(messages: List[Any]) -> List[Dict[str, Any]]:
    """返回前端可识别的消息结构（保留 id / role / content）。"""
    result: List[Dict[str, Any]] = []
    for msg in messages or []:
        if isinstance(msg, dict):
            item = {
                "id": msg.get("id") or "",
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            }
            if msg.get("attachments"):
                item["attachments"] = msg["attachments"]
            result.append(item)
            continue
        result.append(
            {
                "id": getattr(msg, "id", "") or "",
                "role": getattr(msg, "role", "user"),
                "content": getattr(msg, "content", ""),
            }
        )
    return result


async def manage_context_window(
    messages: List[Any],
    *,
    existing_summary: str = "",
    force: bool = False,
) -> Dict[str, Any]:
    """
    检查上下文是否超限；必要时压缩并返回新 messages + summary。

    返回字段：
    - messages: 裁剪后的消息列表（dict）
    - conversationSummary: 更新后的摘要
    - compressed: 是否执行了压缩
    - meta: 给前端的统计信息
    """
    raw_messages = list(messages or [])
    summary = (existing_summary or "").strip()
    keep_recent = get_context_keep_recent_messages()
    max_tokens = get_context_max_tokens()

    token_count = estimate_context_tokens(raw_messages, summary)
    needs_compress = force or (
        is_context_compression_enabled()
        and len(raw_messages) > keep_recent
        and token_count > max_tokens
    )

    meta = {
        "tokenEstimate": token_count,
        "maxTokens": max_tokens,
        "messageCount": len(raw_messages),
        "keepRecent": keep_recent,
        "compressed": False,
        "removedCount": 0,
        "conversationSummary": summary or None,
        "messages": _serialize_messages_for_client(raw_messages),
    }

    if not needs_compress:
        return {
            "messages": raw_messages,
            "conversationSummary": summary,
            "compressed": False,
            "meta": meta,
        }

    if len(raw_messages) <= keep_recent:
        return {
            "messages": raw_messages,
            "conversationSummary": summary,
            "compressed": False,
            "meta": meta,
        }

    old_segment = raw_messages[:-keep_recent]
    recent_segment = raw_messages[-keep_recent:]

    try:
        new_summary = await _summarize_segment(old_segment, summary)
    except Exception as error:
        print(f"[ContextWindow] 摘要失败，回退为截断保留最近消息: {error}")
        new_summary = summary
        if old_segment:
            fallback_lines = []
            for msg in old_segment[-6:]:
                fallback_lines.append(
                    f"- {_message_role(msg)}: {_message_content(msg)[:200]}"
                )
            merged = "\n".join(fallback_lines)
            new_summary = "\n".join(
                part for part in (summary, merged) if part.strip()
            ).strip()
            max_chars = get_context_summary_max_chars()
            if len(new_summary) > max_chars:
                new_summary = new_summary[:max_chars].rstrip() + "…"

    new_token_count = estimate_context_tokens(recent_segment, new_summary)
    meta.update(
        {
            "compressed": True,
            "removedCount": len(old_segment),
            "tokenEstimate": new_token_count,
            "conversationSummary": new_summary or None,
            "messages": _serialize_messages_for_client(recent_segment),
        }
    )

    print(
        f"[ContextWindow] 已压缩 {len(old_segment)} 条历史消息，"
        f"保留最近 {len(recent_segment)} 条，"
        f"token {token_count} → {new_token_count}"
    )

    return {
        "messages": recent_segment,
        "conversationSummary": new_summary,
        "compressed": True,
        "meta": meta,
    }


def conversation_context_for_prompt(
    state: dict,
    *,
    include_last_user: bool = True,
) -> str:
    """拼装写入 LLM prompt 的对话上下文块。"""
    parts: List[str] = []
    summary = (state.get("conversationSummary") or "").strip()
    if summary:
        parts.append(format_summary_block(summary))

    messages = state.get("messages") or []
    if include_last_user and messages:
        last = messages[-1]
        text = _message_content(last)
        if text:
            parts.append(f"## 当前用户消息\n{text}\n")

    return "\n".join(parts).strip()
