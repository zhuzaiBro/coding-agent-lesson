"""问询 / MCP execute_sql 的只读 SQL 守卫。"""
import re

_WRITE_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|COPY|CALL|EXECUTE)\b",
    re.IGNORECASE,
)


def is_read_only_sql(query: str) -> bool:
    """判断查询是否看起来为只读（SELECT / WITH / EXPLAIN 等）。"""
    text = (query or "").strip()
    if not text:
        return False
    if _WRITE_PATTERN.search(text):
        return False
    upper = text.upper()
    return upper.startswith(("SELECT", "WITH", "EXPLAIN", "SHOW", "TABLE"))
