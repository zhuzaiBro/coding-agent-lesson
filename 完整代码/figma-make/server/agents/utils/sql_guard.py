"""Read-only SQL guard for inquiry / MCP execute_sql."""
import re

_WRITE_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|COPY|CALL|EXECUTE)\b",
    re.IGNORECASE,
)


def is_read_only_sql(query: str) -> bool:
    """Return True if query appears to be read-only (SELECT / WITH / EXPLAIN)."""
    text = (query or "").strip()
    if not text:
        return False
    if _WRITE_PATTERN.search(text):
        return False
    upper = text.upper()
    return upper.startswith(("SELECT", "WITH", "EXPLAIN", "SHOW", "TABLE"))
