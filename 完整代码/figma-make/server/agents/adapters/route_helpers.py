"""
路由适配器共用工具。

核心判定：
- has_image_attachment：是否带参考图
- has_text_prompt：是否为有效文本需求（排除「仅粘贴 URL」）
- is_modification_request：是否应在已有项目上迭代修改
"""
import re
from typing import Any, List, Optional


def get_last_message(messages: List[Any]) -> Optional[Any]:
    """Get the last message from the list."""
    if not isinstance(messages, list) or not messages:
        return None
    return messages[-1]


def get_last_text(messages: List[Any]) -> str:
    """Get text content of the last message."""
    last_msg = get_last_message(messages)
    if last_msg is None:
        return ""

    if isinstance(last_msg, dict):
        content = last_msg.get("content", "")
    else:
        content = getattr(last_msg, "content", "")

    return content if isinstance(content, str) else ""


def has_image_attachment(messages: List[Any]) -> bool:
    """Check if the last message has an image attachment."""
    last_msg = get_last_message(messages)
    if not last_msg:
        return False

    if isinstance(last_msg, dict):
        attachments = last_msg.get("attachments", [])
    else:
        attachments = getattr(last_msg, "attachments", [])

    if not isinstance(attachments, list):
        return False

    return any(
        (att.get("type") == "image" and att.get("url")) if isinstance(att, dict)
        else False
        for att in attachments
    )


def has_text_prompt(messages: List[Any]) -> bool:
    """
    Check if the last message has a text prompt (after removing URLs).

    Avoids mis-classifying messages that only contain a URL as text prompts.
    """
    content = get_last_text(messages)
    text_without_urls = re.sub(r"https?://\S+", "", content).strip()
    return len(text_without_urls) > 0


def _has_existing_project_files(context: dict) -> bool:
    raw = context.get("existingFiles") or context.get("files")
    if not isinstance(raw, dict) or not raw:
        return False
    return len(raw) > 0


def is_modification_request(messages: List[Any], *, context: dict | None = None) -> bool:
    """
    判定是否走 modification 轻量图。

    规则：
    1. 无 existingFiles → 一定不是修改
    2. 有文件且用户未说「从零/重做」→ 默认视为修改
    3. 有文件且含修改类关键词 → 修改
    """
    content = get_last_text(messages).lower()
    ctx = context or {}
    has_files = _has_existing_project_files(ctx)

    rebuild_keywords = [
        "从零", "重新生成", "新建项目", "重做", "换一个应用",
        "start over", "from scratch", "new project", "regenerate all",
    ]
    if not has_files:
        return False

    if content and not any(k in content for k in rebuild_keywords):
        return True

    if not content:
        return False

    keywords = [
        "modify", "update", "refactor", "change", "adjust", "fix", "tweak",
        "修改", "改一下", "优化", "重构", "在现有", "基于当前", "调整", "改成", "换成",
        "增加", "删除", "添加", "去掉", "样式", "颜色", "按钮",
    ]
    return any(k in content for k in keywords)
