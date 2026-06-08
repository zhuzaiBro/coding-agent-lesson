"""Shared helpers for Supabase MCP subgraph nodes."""
import json
import re


def parse_publishable_anon_key(keys_text: str) -> str:
    """Best-effort extract anon/public key from MCP text/json."""
    if not keys_text:
        return ""
    try:
        data = json.loads(keys_text)
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", "")).lower()
                if "anon" in name or "public" in name:
                    return str(item.get("api_key") or item.get("key") or "")
        if isinstance(data, dict):
            return str(data.get("anon_key") or data.get("anon") or "")
    except json.JSONDecodeError:
        pass
    match = re.search(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", keys_text)
    return match.group(0) if match else ""
