"""
Route adapter shared helper functions.
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
    Modification route when:
    - User has an existing project (files in request) and is not asking to rebuild from scratch, or
    - Message contains explicit edit keywords.
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
