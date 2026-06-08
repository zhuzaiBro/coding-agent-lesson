"""
Inquiry 分支测试 — QA + needsDatabase 走 supabase → inquiry → chatReply

    cd server && uv run python tests/test_inquiry_flow.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.flows.traditional.analysis.nodes.analysis_router import route_after_analysis
from agents.flows.traditional.inquiry.nodes.chat_reply_node import chat_reply_node
from agents.flows.traditional.inquiry.nodes.database_inquiry_node import database_inquiry_node
from agents.graphs.traditional_graph import build_traditional_agent


def test_route_database_inquiry() -> None:
    state = {
        "analysis": {
            "type": "QA",
            "needsDatabase": True,
            "databaseReason": "需查询订单计算链路",
        },
    }
    with patch("agents.utils.supabase_integration.is_supabase_configured", return_value=True):
        assert route_after_analysis(state) == "database_inquiry"

    state["analysis"]["needsDatabase"] = False
    assert route_after_analysis(state) == "conversational"

    state["analysis"] = {"type": "CREATE", "needsDatabase": True}
    with patch("agents.utils.supabase_integration.is_supabase_configured", return_value=True):
        assert route_after_analysis(state) == "generation"


async def test_inquiry_mock_roundtrip() -> None:
    """inquiryNode mock → chatReplyNode 透传"""
    inquiry_out = await database_inquiry_node({
        "messages": [{"role": "user", "content": "检查订单 ORD-1 计算链路"}],
        "mockConfig": {"inquiryNode": True},
        "analysis": {"type": "QA", "needsDatabase": True},
    })
    assert inquiry_out.get("inquiry", {}).get("message")

    reply_out = await chat_reply_node({**inquiry_out})
    assert reply_out["chatReply"]["message"]
    assert reply_out["chatReply"].get("inquiry")


async def test_inquiry_sql_loop_mock_mcp() -> None:
    """Mock MCP + 结构化 LLM 两步：query → answer"""
    from agents.flows.traditional.inquiry.schemas.inquiry_schema import InquiryAction, InquiryStep

    query_step = InquiryStep(
        action=InquiryAction.QUERY,
        sql="SELECT id, total FROM orders WHERE id = 'ORD-1' LIMIT 1",
        message="先查订单主表",
    )
    answer_step = InquiryStep(
        action=InquiryAction.ANSWER,
        message="订单 ORD-1 总金额 100 元，与明细一致。",
    )

    call_count = 0

    async def fake_ainvoke(_prompt):
        nonlocal call_count
        call_count += 1
        return query_step if call_count == 1 else answer_step

    mock_model = MagicMock()
    mock_model.ainvoke = AsyncMock(side_effect=fake_ainvoke)

    mock_client = MagicMock()
    mock_client.execute_sql = AsyncMock(return_value="id=ORD-1, total=100")

    with (
        patch("agents.flows.traditional.inquiry.nodes.database_inquiry_node.is_supabase_configured", return_value=True),
        patch("agents.flows.traditional.inquiry.nodes.database_inquiry_node.get_structured_model", return_value=mock_model),
        patch("agents.flows.traditional.inquiry.nodes.database_inquiry_node.get_supabase_mcp_client", return_value=mock_client),
    ):
        out = await database_inquiry_node({
            "messages": [{"role": "user", "content": "检查订单 ORD-1"}],
            "analysis": {"type": "QA", "needsDatabase": True, "summary": "订单排查"},
            "supabase": {
                "enabled": True,
                "schemaSummary": "### public.orders\n- id text\n- total numeric",
            },
        })

    inquiry = out["inquiry"]
    assert inquiry["status"] == "ok"
    assert len(inquiry["trace"]) == 1
    assert "ORD-1" in inquiry["message"]


async def test_graph_has_inquiry_edges() -> None:
    agent = build_traditional_agent()
    nodes = agent.get_graph().nodes
    assert "inquiryNode" in nodes
    assert "chatReplyNode" in nodes


async def main() -> None:
    print("=== Inquiry 路由 ===")
    test_route_database_inquiry()
    print("✓ 路由测试通过\n")

    print("=== Inquiry Mock 往返 ===")
    await test_inquiry_mock_roundtrip()
    print("✓ Mock 往返通过\n")

    print("=== Inquiry SQL 循环 ===")
    await test_inquiry_sql_loop_mock_mcp()
    print("✓ SQL 循环通过\n")

    print("=== 图结构 ===")
    await test_graph_has_inquiry_edges()
    print("✓ 图结构通过\n")

    print("=" * 40)
    print("Inquiry 分支全部测试通过")
    print("=" * 40)


if __name__ == "__main__":
    asyncio.run(main())
