"""Figma Remote MCP OAuth — 浏览器打开 https://www.figma.com/oauth/mcp 授权。"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import httpx

from config.figma import get_oauth_redirect_uri

_OAUTH_METADATA_URL = "https://mcp.figma.com/.well-known/oauth-authorization-server"
_OAUTH_SCOPES = "mcp:connect"

_metadata_cache: Optional[Dict[str, Any]] = None
_client_cache: Optional[Dict[str, str]] = None
_user_clients: Dict[str, Dict[str, str]] = {}
_sessions: Dict[str, Dict[str, Any]] = {}
_state_to_sid: Dict[str, str] = {}


def set_user_oauth_client(config_sid: str, client_id: str, client_secret: str) -> None:
    global _client_cache
    _client_cache = None
    _user_clients[config_sid] = {
        "client_id": client_id.strip(),
        "client_secret": client_secret.strip(),
    }


def clear_user_oauth_client(config_sid: Optional[str]) -> None:
    global _client_cache
    if config_sid and config_sid in _user_clients:
        del _user_clients[config_sid]
    _client_cache = None


def _pkce_pair() -> Tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def get_oauth_metadata() -> Dict[str, Any]:
    global _metadata_cache
    if _metadata_cache is None:
        response = httpx.get(_OAUTH_METADATA_URL, timeout=30.0)
        response.raise_for_status()
        _metadata_cache = response.json()
    return _metadata_cache


def _get_or_register_client(
    redirect_uri: str,
    user_config_sid: Optional[str] = None,
) -> Dict[str, str]:
    global _client_cache

    if user_config_sid and user_config_sid in _user_clients:
        return _user_clients[user_config_sid]

    if _client_cache:
        return _client_cache

    client_id = os.getenv("FIGMA_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.getenv("FIGMA_OAUTH_CLIENT_SECRET", "").strip()
    if client_id and client_secret:
        _client_cache = {"client_id": client_id, "client_secret": client_secret}
        return _client_cache

    meta = get_oauth_metadata()
    register_url = meta.get("registration_endpoint", "https://api.figma.com/v1/oauth/mcp/register")
    response = httpx.post(
        register_url,
        json={
            "client_name": os.getenv("FIGMA_OAUTH_APP_NAME", "Zood Figma Make"),
            "redirect_uris": [redirect_uri],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "client_secret_post",
        },
        timeout=30.0,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            "未配置 Figma OAuth 客户端。请点击 Figma 按钮，在弹窗中填写 "
            "Client ID / Client Secret（回调地址填 "
            f"{redirect_uri}）"
        )

    data = response.json()
    _client_cache = {
        "client_id": data["client_id"],
        "client_secret": data.get("client_secret", ""),
    }
    print(
        "[Figma OAuth] 已注册 MCP OAuth 客户端，建议将 ID/SECRET 写入 .env 以免重启丢失"
    )
    return _client_cache


def start_authorization(
    user_config_sid: Optional[str] = None,
) -> Tuple[str, str]:
    """返回 (authorize_url, session_id)。"""
    redirect_uri = get_oauth_redirect_uri()
    client = _get_or_register_client(redirect_uri, user_config_sid)
    meta = get_oauth_metadata()

    session_id = secrets.token_urlsafe(16)
    state = secrets.token_urlsafe(24)
    verifier, challenge = _pkce_pair()

    _sessions[session_id] = {
        "state": state,
        "code_verifier": verifier,
        "config_sid": user_config_sid,
        "created_at": time.time(),
    }
    _state_to_sid[state] = session_id

    params = {
        "client_id": client["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "scope": _OAUTH_SCOPES,
    }
    authorize_url = f"{meta['authorization_endpoint']}?{urlencode(params)}"
    return authorize_url, session_id


def complete_authorization(code: str, state: str) -> Optional[str]:
    session_id = _state_to_sid.pop(state, None)
    if not session_id or session_id not in _sessions:
        return None
    session = _sessions[session_id]
    if session.get("state") != state:
        return None

    redirect_uri = get_oauth_redirect_uri()
    config_sid = session.get("config_sid")
    client = _get_or_register_client(redirect_uri, config_sid)
    meta = get_oauth_metadata()

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client["client_id"],
        "code_verifier": session["code_verifier"],
    }
    if client.get("client_secret"):
        payload["client_secret"] = client["client_secret"]

    response = httpx.post(meta["token_endpoint"], data=payload, timeout=30.0)
    response.raise_for_status()
    tokens = response.json()

    session.update(
        {
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "expires_at": time.time() + int(tokens.get("expires_in", 3600)),
        }
    )
    return session_id


def get_access_token_for_session(session_id: Optional[str]) -> Optional[str]:
    if not session_id or session_id not in _sessions:
        return None
    session = _sessions[session_id]
    token = session.get("access_token")
    if not token:
        return None
    if session.get("expires_at", 0) < time.time() + 30:
        return None
    return str(token)


def clear_session(session_id: Optional[str]) -> None:
    if session_id and session_id in _sessions:
        state = _sessions[session_id].get("state")
        if state and _state_to_sid.get(state) == session_id:
            _state_to_sid.pop(state, None)
        del _sessions[session_id]
