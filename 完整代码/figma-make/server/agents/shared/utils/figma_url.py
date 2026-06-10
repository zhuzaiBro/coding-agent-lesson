"""
Figma URL 检测工具（单一来源）

路由分流的核心判断逻辑：只要消息中含 Figma URL 就走 figma 流程。
倒序遍历消息列表，优先使用最新消息中的 URL（支持用户在对话中途更换设计稿）。
"""
import re
from typing import List, Optional

# Figma URL 正则，支持：
#   https://www.figma.com/file/xxx
#   https://www.figma.com/design/xxx
#   https://www.figma.com/proto/xxx
#   https://www.figma.com/board/xxx
FIGMA_URL_REGEX = re.compile(
    r"https?://([\w.-]+\.)?figma\.com/(file|design|proto|board)/[\w-]+[^\s)\}\]\"]*",
    re.IGNORECASE,
)


def extract_figma_url(messages: List[any]) -> Optional[str]:
    """
    从消息列表中提取 Figma URL。

    倒序遍历，优先取最新消息中的链接。

    Args:
        messages: 消息对象列表
    Returns:
        Figma URL 字符串，未找到则返回 None
    """
    if not messages or not isinstance(messages, list):
        return None

    # 倒序遍历，优先使用最新 URL
    for msg in reversed(messages):
        # 提取消息文本（支持字符串与 content 数组格式）
        if isinstance(msg, dict):
            content = msg.get("content", "")
        else:
            content = getattr(msg, "content", "")

        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = " ".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            )
        else:
            text = str(content) if content else ""

        m = FIGMA_URL_REGEX.search(text)
        if m:
            return m.group(0)

    return None
