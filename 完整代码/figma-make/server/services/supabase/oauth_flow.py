"""Supabase MCP OAuth 2.1 (PKCE) — 浏览器授权后由服务端持有 access token。"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import httpx

from config.app_urls import get_frontend_origin, get_supabase_oauth_redirect_uri

_OAUTH_METADATA_URL = "https://api.supabase.com/.well-known/oauth-authorization-server"
_OAUTH_SCOPES = (
    "organizations:read projects:read projects:write "
    "database:read database:write"
)

_metadata_cache: Optional[Dict[str, Any]] = None
_client_cache: Optional[Dict[str, str]] = None
# session_id -> { state, code_verifier, access_token?, refresh_token?, expires_at? }
_sessions: Dict[str, Dict[str, Any]] = {}
_state_to_sid: Dict[str, str] = {}


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


def get_oauth_redirect_uri() -> str:
    return get_supabase_oauth_redirect_uri()


def resolve_frontend_origin(session_id: Optional[str]) -> str:
    if session_id and session_id in _sessions:
        origin = _sessions[session_id].get("frontend_origin")
        if origin:
            return str(origin).rstrip("/")
    return get_frontend_origin()


def _get_or_register_client(redirect_uri: str) -> Dict[str, str]:
    global _client_cache
    if _client_cache:
        return _client_cache

    client_id = os.getenv("SUPABASE_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.getenv("SUPABASE_OAUTH_CLIENT_SECRET", "").strip()
    if client_id and client_secret:
        _client_cache = {"client_id": client_id, "client_secret": client_secret}
        return _client_cache

    meta = get_oauth_metadata()
    response = httpx.post(
        meta["registration_endpoint"],
        json={
            "client_name": os.getenv("SUPABASE_OAUTH_APP_NAME", "Zood Figma Make"),
            "redirect_uris": [redirect_uri],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "client_secret_post",
        },
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    _client_cache = {
        "client_id": data["client_id"],
        "client_secret": data.get("client_secret", ""),
    }
    print(
        "[Supabase OAuth] Dynamic client registered. "
        "Set SUPABASE_OAUTH_CLIENT_ID/SECRET in .env to persist across restarts."
    )
    return _client_cache


def start_authorization(frontend_origin: str = "") -> Tuple[str, str]:
    """返回 (authorize_url, session_id)。"""
    redirect_uri = get_oauth_redirect_uri()
    client = _get_or_register_client(redirect_uri)
    meta = get_oauth_metadata()

    session_id = secrets.token_urlsafe(16)
    state = secrets.token_urlsafe(24)
    verifier, challenge = _pkce_pair()

    origin = frontend_origin.strip() or None
    _sessions[session_id] = {
        "state": state,
        "code_verifier": verifier,
        "created_at": time.time(),
        "frontend_origin": origin,
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
    """用授权码换 token，返回 session_id。"""
    session_id = _state_to_sid.pop(state, None)
    if not session_id or session_id not in _sessions:
        return None

    session = _sessions[session_id]
    if session.get("state") != state:
        return None

    redirect_uri = get_oauth_redirect_uri()
    client = _get_or_register_client(redirect_uri)
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

    expires_in = int(tokens.get("expires_in", 3600))
    session.update(
        {
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "expires_at": time.time() + expires_in,
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
    expires_at = session.get("expires_at", 0)
    if expires_at and expires_at < time.time() + 30:
        # TODO: refresh_token flow when expired
        return None
    return str(token)


def clear_session(session_id: Optional[str]) -> None:
    if session_id and session_id in _sessions:
        state = _sessions[session_id].get("state")
        if state and _state_to_sid.get(state) == session_id:
            _state_to_sid.pop(state, None)
        del _sessions[session_id]
