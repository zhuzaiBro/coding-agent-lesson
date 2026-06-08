"""Safe accessors for LangGraph state / node output dicts."""
from typing import Any, Dict, List


def as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def dict_list(parent: Any, key: str) -> List[dict]:
    """Return parent[key] as a list of dicts; never None."""
    if not isinstance(parent, dict):
        return []
    raw = parent.get(key)
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def as_dict_list(value: Any) -> List[dict]:
    """Return a top-level list value as list of dicts; never None."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
