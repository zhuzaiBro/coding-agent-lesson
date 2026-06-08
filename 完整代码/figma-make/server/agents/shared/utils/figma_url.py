"""
Figma URL 检测工具（单一来源）

路由分流的核心判断逻辑：只要消息中含 Figma URL 就走 figma 流程。
倒序遍历消息列表，优先使用最新消息中的 URL（支持用户在对话中途更换设计稿）。
"""
import re
from typing import List, Optional

# Figma URL regex pattern
# Supports:
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
    Extract Figma URL from message list.

    Iterates in reverse order (most recent message first).

    Args:
        messages: List of message objects
    Returns:
        Figma URL string or None
    """
    if not messages or not isinstance(messages, list):
        return None

    # Iterate in reverse order, prioritize most recent URL
    for msg in reversed(messages):
        # Extract message text content (supports string and content array formats)
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
