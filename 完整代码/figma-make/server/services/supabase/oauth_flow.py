"""Supabase MCP OAuth 2.1 (PKCE) — 浏览器授权后由服务端持有 access token（持久化）。"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import httpx

from config.app_urls import (
    get_supabase_oauth_redirect_uri,
    normalize_frontend_origin,
)
from services.oauth_session_store import get_supabase_oauth_store
from services.oauth_token_refresh import ensure_fresh_access_token

_OAUTH_METADATA_URL = "https://api.supabase.com/.well-known/oauth-authorization-server"
_OAUTH_SCOPES = (
    "organizations:read projects:read projects:write "
    "database:read database:write"
)

_metadata_cache: Optional[Dict[str, Any]] = None
_client_cache: Optional[Dict[str, str]] = None
_store = get_supabase_oauth_store()


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
    stored: Optional[str] = None
    session = _store.get_session(session_id)
    if session:
        raw = session.get("frontend_origin")
        if raw:
            stored = str(raw).rstrip("/")
    resolved = normalize_frontend_origin(stored)
    if stored and resolved != stored:
        print(
            f"[Supabase OAuth] 忽略前端 origin {stored}，"
            f"改跳 {resolved}（线上 API 须在同站前端完成授权回调）"
        )
    return resolved


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
    _store.set_session(
        session_id,
        {
            "state": state,
            "code_verifier": verifier,
            "created_at": time.time(),
            "frontend_origin": origin,
        },
    )
    _store.map_state(state, session_id)

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
    print(f"[Supabase OAuth] redirect_uri={redirect_uri}")
    return authorize_url, session_id


def complete_authorization(code: str, state: str) -> Optional[str]:
    """用授权码换 token，返回 session_id。"""
    session_id = _store.pop_state(state)
    session = _store.get_session(session_id)
    if not session_id or not session:
        return None
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
            "authorized_at": time.time(),
        }
    )
    session.pop("code_verifier", None)
    _store.set_session(session_id, session)
    return session_id


def get_session_project(session_id: Optional[str]) -> Optional[Dict[str, str]]:
    """返回 OAuth 会话中用户选择的项目 {ref, name}。"""
    session = _store.get_session(session_id)
    if not session:
        return None
    ref = (session.get("project_ref") or "").strip()
    if not ref:
        return None
    return {
        "ref": ref,
        "name": (session.get("project_name") or ref).strip() or ref,
    }


def set_session_project(
    session_id: str,
    project_ref: str,
    project_name: str = "",
) -> None:
    """将用户选择的项目写入 OAuth 会话。"""
    ref = (project_ref or "").strip()
    if not ref or not _store.get_session(session_id):
        return
    _store.update_session(
        session_id,
        project_ref=ref,
        project_name=(project_name or ref).strip() or ref,
    )
    print(f"[Supabase OAuth] 会话 {session_id[:8]}… 已选择项目 {ref}")


def get_project_ref_for_session(session_id: Optional[str]) -> Optional[str]:
    info = get_session_project(session_id)
    return info["ref"] if info else None


def _persist_session(session_id: str, session: Dict[str, Any]) -> None:
    _store.set_session(session_id, session)


def get_access_token_for_session(session_id: Optional[str]) -> Optional[str]:
    session = _store.get_session(session_id)
    if not session:
        return None
    return ensure_fresh_access_token(
        session_id,
        session,
        get_client=lambda: _get_or_register_client(get_oauth_redirect_uri()),
        token_endpoint=get_oauth_metadata()["token_endpoint"],
        persist=_persist_session,
        provider_label="Supabase",
    )


def clear_session(session_id: Optional[str]) -> None:
    _store.delete_session(session_id)
