"""
Agent 节点 Mock 工具

用于调试阶段跳过真实 LLM 调用，直接返回本地 mock/*.json 文件的数据。

Mock 生效优先级（高 → 低）：
  1. 请求体中的 mockConfig（按节点精细控制）
  2. 环境变量 MOCK_MODE=true（全局开关）
  3. 默认不 Mock

Mock 数据文件放在项目根目录 mock/ 文件夹下，如 mock/analysisResult.json。
"""
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Callable, Optional, Union


def should_mock(state: dict, node_name: str) -> bool:
    """
    Determine if the specified node should use mock data.
    Priority: State mockConfig > MOCK_MODE env var.

    Args:
        state: Current graph state
        node_name: Node name (e.g. 'uiNode', 'analysisNode')
    Returns:
        bool
    """
    mock_config = state.get("mockConfig", {}) or {}
    if node_name in mock_config and isinstance(mock_config[node_name], bool):
        return mock_config[node_name]

    # Fallback: use MOCK_MODE env var
    return os.getenv("MOCK_MODE", "false").lower() == "true"


async def try_execute_mock(
    state: dict,
    node_name: str,
    mock_file_name: str,
    process_result: Union[str, Callable[[Any, Any], Any]],
) -> Optional[Any]:
    """
    Try to execute mock strategy for a node.

    Args:
        state: Current graph state
        node_name: Node name (for shouldMock and logging)
        mock_file_name: Mock file name (e.g. 'analysisResult.json')
        process_result: Either a string key to wrap result under, or callable(data, state) -> any
    Returns:
        Mock result dict if mock was executed, None otherwise.
    """
    if not should_mock(state, node_name):
        return None

    print(f"--- {node_name} Head Start (MOCK) ---")

    # Simulate delay
    await asyncio.sleep(0.1)

    try:
        mock_path = Path(os.getcwd()) / "mock" / mock_file_name
        file_content = mock_path.read_text(encoding="utf-8")
        json_data = json.loads(file_content)

        print(f"--- {node_name} End (MOCK) ---")

        if isinstance(process_result, str):
            return {process_result: json_data}
        elif callable(process_result):
            return process_result(json_data, state)

        return json_data

    except Exception as e:
        print(f"[MOCK] Failed to read mock data for {node_name}: {e}")
        return None
