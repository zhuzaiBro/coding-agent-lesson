"""LangGraph state / 节点输出字典的安全访问工具。"""
from typing import Any, Dict, List


def as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def dict_list(parent: Any, key: str) -> List[dict]:
    """返回 parent[key] 的字典列表，永不为 None。"""
    if not isinstance(parent, dict):
        return []
    raw = parent.get(key)
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def as_dict_list(value: Any) -> List[dict]:
    """将顶层列表值转为字典列表，永不为 None。"""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
