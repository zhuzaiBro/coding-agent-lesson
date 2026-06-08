"""
Supabase 子图测试 — 可直接运行查看输出：

    cd server && uv run python tests/test_supabase_graph.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# 保证从 server/ 根目录可 import agents.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.graphs.supabase_graph import supabase_graph
from agents.graphs.traditional_graph import run_supabase_graph
from agents.utils.supabase_integration import (
    format_supabase_prompt_block,
    needs_database_connection,
)


def _fake_mcp_client() -> MagicMock:
    client = MagicMock()
    client.ping = AsyncMock(
        return_value={"ok": True, "projectUrl": "https://demo-project.supabase.co", "mcpUrl": "https://mcp.supabase.com/mcp"}
    )
    client.get_project_url = AsyncMock(return_value="https://demo-project.supabase.co")
    client.get_publishable_keys = AsyncMock(
        return_value='[{"name":"anon","api_key":"eyJhbGciOiJIUzI1NiJ9.fake.token"}]'
    )
    client.list_tables = AsyncMock(
        return_value="### public.todos\n- id: uuid (pk)\n- title: text\n- done: boolean"
    )
    client.generate_typescript_types = AsyncMock(
        return_value="export type Todo = { id: string; title: string; done: boolean }"
    )
    return client


async def test_subgraph_all_nodes_with_mock_mcp() -> None:
    """子图 5 节点串行：connect → config → schema → types → assemble"""
    print("\n=== 1. Supabase 子图（Mock MCP）===\n")

    with (
        patch("agents.flows.traditional.architecture.nodes.supabase_connect_node.get_supabase_mcp_client", return_value=_fake_mcp_client()),
        patch("agents.flows.traditional.architecture.nodes.supabase_fetch_config_node.get_supabase_mcp_client", return_value=_fake_mcp_client()),
        patch("agents.flows.traditional.architecture.nodes.supabase_fetch_schema_node.get_supabase_mcp_client", return_value=_fake_mcp_client()),
        patch("agents.flows.traditional.architecture.nodes.supabase_fetch_types_node.get_supabase_mcp_client", return_value=_fake_mcp_client()),
        patch(
            "agents.flows.traditional.architecture.nodes.supabase_fetch_types_node.is_read_only",
            return_value=False,
        ),
        patch(
            "agents.flows.traditional.architecture.nodes.supabase_assemble_node.is_read_only",
            return_value=False,
        ),
    ):
        result = await supabase_graph.ainvoke({"useSupabase": True})

    supabase = result.get("supabase", {})
    assert supabase.get("enabled") is True
    assert "demo-project" in supabase.get("projectUrl", "")
    assert "todos" in supabase.get("schemaSummary", "").lower()
    assert "Todo" in supabase.get("typescriptTypes", "")

    print(json.dumps(supabase, ensure_ascii=False, indent=2))
    print("\n--- 注入 service/hooks 的 prompt 片段 ---\n")
    print(format_supabase_prompt_block(supabase)[:600], "...\n")
    print("✓ 子图测试通过")


async def test_subgraph_mcp_failure() -> None:
    """MCP 连接失败时 assemble 应返回 enabled=false + error"""
    print("\n=== 2. Supabase 子图（MCP 失败路径）===\n")

    broken = MagicMock()
    broken.ping = AsyncMock(side_effect=RuntimeError("401 Unauthorized — token expired"))

    with patch(
        "agents.flows.traditional.architecture.nodes.supabase_connect_node.get_supabase_mcp_client",
        return_value=broken,
    ):
        result = await supabase_graph.ainvoke({"useSupabase": True})

    supabase = result.get("supabase", {})
    assert supabase.get("enabled") is False
    assert "401" in supabase.get("error", "")

    print(json.dumps(supabase, ensure_ascii=False, indent=2))
    print("\n✓ 失败路径测试通过")


async def test_bridge_skip_when_not_requested() -> None:
    """未配置 needsDatabase 且无显式开关时 bridge 跳过"""
    print("\n=== 3. Bridge 跳过（无联库需求）===\n")

    with patch("config.supabase.is_supabase_configured", return_value=True):
        out = await run_supabase_graph({
            "analysis": {"needsDatabase": False},
            "messages": [],
        })

    assert out == {}
    print("bridge 返回: {}")
    print("\n✓ 跳过逻辑测试通过")


async def test_bridge_mock_json() -> None:
    """Bridge 使用 mock/supabaseResult.json（与 componentSubgraph 同模式）"""
    print("\n=== 4. Bridge Mock（mock/supabaseResult.json）===\n")

    with patch(
        "agents.graphs.traditional_graph.needs_database_connection",
        return_value=True,
    ):
        out = await run_supabase_graph({
            "useSupabase": True,
            "mockConfig": {"supabaseSubgraph": True},
        })

    supabase = out.get("supabase", {})
    assert supabase.get("enabled") is True
    assert "abcdefgh" in supabase.get("projectUrl", "")

    print(json.dumps(supabase, ensure_ascii=False, indent=2))
    print("\n✓ Bridge Mock 测试通过")


async def test_needs_database_connection_llm_judgment() -> None:
    """LLM analysis.needsDatabase 驱动联库，不再依赖关键词"""
    print("\n=== 5. needsDatabase 抽象判断 ===\n")

    with patch("agents.utils.supabase_integration.is_supabase_configured", return_value=True):
        # 订单链路排查 — 无 supabase 关键词也应联库
        qa_state = {
            "messages": [{"role": "user", "content": "帮我检查下订单 ORD-8821 的计算数据链路"}],
            "analysis": {
                "type": "QA",
                "needsDatabase": True,
                "databaseReason": "需要查询订单及相关计算表中的真实数据",
            },
        }
        assert needs_database_connection(qa_state) is True

        # 纯 UI — 不联库
        ui_state = {
            "messages": [{"role": "user", "content": "做一个好看的落地页"}],
            "analysis": {"type": "CREATE", "needsDatabase": False},
        }
        assert needs_database_connection(ui_state) is False

        # 用户显式关闭
        assert needs_database_connection({**qa_state, "useSupabase": False}) is False
        # 用户显式开启（即使 analysis 为 false）
        assert needs_database_connection({**ui_state, "useSupabase": True}) is True

    print("  QA 订单排查 → needsDatabase=True → 联库 ✓")
    print("  纯 UI → needsDatabase=False → 跳过 ✓")
    print("  useSupabase 显式开关优先 ✓")
    print("\n✓ needsDatabase 判断测试通过")


async def test_bridge_skip_when_llm_says_no_db() -> None:
    """analysis.needsDatabase=false 时 bridge 跳过"""
    print("\n=== 6. Bridge 跳过（LLM needsDatabase=false）===\n")

    with patch("config.supabase.is_supabase_configured", return_value=True):
        out = await run_supabase_graph({
            "analysis": {"needsDatabase": False},
            "messages": [{"role": "user", "content": "做一个静态展示页"}],
        })

    assert out == {}
    print("bridge 返回: {}")
    print("\n✓ LLM 判定不联库时跳过")


async def main() -> None:
    await test_subgraph_all_nodes_with_mock_mcp()
    await test_subgraph_mcp_failure()
    await test_bridge_skip_when_not_requested()
    await test_bridge_mock_json()
    await test_needs_database_connection_llm_judgment()
    await test_bridge_skip_when_llm_says_no_db()
    print("\n" + "=" * 48)
    print("全部 6 项 Supabase 子图测试通过")
    print("=" * 48 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except AssertionError as exc:
        print(f"\n✗ 断言失败: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"\n✗ 运行失败: {exc}", file=sys.stderr)
        raise
