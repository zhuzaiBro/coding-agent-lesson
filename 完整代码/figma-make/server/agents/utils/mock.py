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
    判断指定节点是否应使用 Mock 数据。
    优先级：state.mockConfig > MOCK_MODE 环境变量。

    Args:
        state: 当前图状态
        node_name: 节点名（如 'uiNode'、'analysisNode'）
    Returns:
        是否启用 Mock
    """
    mock_config = state.get("mockConfig", {}) or {}
    if node_name in mock_config and isinstance(mock_config[node_name], bool):
        return mock_config[node_name]

    # 兜底：使用 MOCK_MODE 环境变量
    return os.getenv("MOCK_MODE", "false").lower() == "true"


async def try_execute_mock(
    state: dict,
    node_name: str,
    mock_file_name: str,
    process_result: Union[str, Callable[[Any, Any], Any]],
) -> Optional[Any]:
    """
    尝试对节点执行 Mock 策略。

    Args:
        state: 当前图状态
        node_name: 节点名（用于 should_mock 与日志）
        mock_file_name: Mock 文件名（如 'analysisResult.json'）
        process_result: 包装结果的 state 键名，或 callable(data, state) -> any
    Returns:
        若执行了 Mock 则返回结果 dict，否则返回 None。
    """
    if not should_mock(state, node_name):
        return None

    print(f"--- {node_name} 开始 (MOCK) ---")

    # 模拟延迟
    await asyncio.sleep(0.1)

    try:
        mock_path = Path(os.getcwd()) / "mock" / mock_file_name
        file_content = mock_path.read_text(encoding="utf-8")
        json_data = json.loads(file_content)

        print(f"--- {node_name} 结束 (MOCK) ---")

        if isinstance(process_result, str):
            return {process_result: json_data}
        elif callable(process_result):
            return process_result(json_data, state)

        return json_data

    except Exception as e:
        print(f"[MOCK] 读取 {node_name} 的 Mock 数据失败: {e}")
        return None
