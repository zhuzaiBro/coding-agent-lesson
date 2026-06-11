"""OAuth access_token 过期时用 refresh_token 续期。"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

import httpx


def refresh_access_token(
    *,
    token_endpoint: str,
    client: Dict[str, str],
    refresh_token: str,
) -> Dict[str, Any]:
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client["client_id"],
    }
    if client.get("client_secret"):
        payload["client_secret"] = client["client_secret"]

    response = httpx.post(token_endpoint, data=payload, timeout=30.0)
    response.raise_for_status()
    return response.json()


def ensure_fresh_access_token(
    session_id: str,
    session: Dict[str, Any],
    *,
    get_client: Callable[[], Dict[str, str]],
    token_endpoint: str,
    persist: Callable[[str, Dict[str, Any]], None],
    provider_label: str,
) -> Optional[str]:
    """若 access_token 将过期则刷新并写回持久化存储。"""
    token = session.get("access_token")
    if not token:
        return None

    expires_at = float(session.get("expires_at") or 0)
    if expires_at and expires_at >= time.time() + 60:
        return str(token)

    refresh = session.get("refresh_token")
    if not refresh:
        print(f"[{provider_label} OAuth] access_token 已过期且无 refresh_token")
        return None

    try:
        tokens = refresh_access_token(
            token_endpoint=token_endpoint,
            client=get_client(),
            refresh_token=str(refresh),
        )
    except Exception as error:
        print(f"[{provider_label} OAuth] refresh_token 失败: {error}")
        return None

    expires_in = int(tokens.get("expires_in", 3600))
    session.update(
        {
            "access_token": tokens.get("access_token") or token,
            "refresh_token": tokens.get("refresh_token") or refresh,
            "expires_at": time.time() + expires_in,
            "refreshed_at": time.time(),
        }
    )
    persist(session_id, session)
    print(f"[{provider_label} OAuth] access_token 已刷新（session {session_id[:8]}…）")
    return str(session["access_token"])
