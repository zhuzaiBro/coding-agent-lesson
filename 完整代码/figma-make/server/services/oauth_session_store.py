"""
MCP OAuth 会话持久化（Supabase / Figma）。

默认写入 server/data/oauth/{provider}_sessions.json，服务重启后仍可通过
Cookie 中的 session_id 恢复 access_token、project_ref、Figma 客户端凭证等。
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional


def _data_dir() -> Path:
    custom = os.getenv("OAUTH_SESSION_DATA_DIR", "").strip()
    if custom:
        return Path(custom)
    return Path(__file__).resolve().parent.parent / "data" / "oauth"


class OAuthSessionStore:
    """线程安全的 JSON 文件存储。"""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        self._path = _data_dir() / f"{provider}_sessions.json"
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {
            "sessions": {},
            "state_to_sid": {},
        }
        if provider == "figma":
            self._data["user_clients"] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                sessions = raw.get("sessions")
                state_map = raw.get("state_to_sid")
                if isinstance(sessions, dict):
                    self._data["sessions"] = sessions
                if isinstance(state_map, dict):
                    self._data["state_to_sid"] = state_map
                if self.provider == "figma" and isinstance(raw.get("user_clients"), dict):
                    self._data["user_clients"] = raw["user_clients"]
            count = len(self._data.get("sessions") or {})
            if count:
                print(f"[OAuthStore:{self.provider}] 已加载 {count} 个持久化会话")
        except Exception as error:
            print(f"[OAuthStore:{self.provider}] 读取失败: {error}")

    def _save_locked(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(self._path)

    def _mutate(self, fn) -> Any:
        with self._lock:
            result = fn()
            self._save_locked()
            return result

    def get_session(self, session_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        with self._lock:
            session = self._data["sessions"].get(session_id)
            return dict(session) if isinstance(session, dict) else None

    def set_session(self, session_id: str, session: Dict[str, Any]) -> None:
        def _write():
            self._data["sessions"][session_id] = dict(session)
        self._mutate(_write)

    def update_session(self, session_id: str, **updates: Any) -> None:
        def _write():
            current = self._data["sessions"].get(session_id)
            if not isinstance(current, dict):
                return
            current.update(updates)
            self._data["sessions"][session_id] = current
        self._mutate(_write)

    def delete_session(self, session_id: Optional[str]) -> None:
        if not session_id:
            return

        def _write():
            session = self._data["sessions"].pop(session_id, None)
            if isinstance(session, dict):
                state = session.get("state")
                if state and self._data["state_to_sid"].get(state) == session_id:
                    self._data["state_to_sid"].pop(state, None)
        self._mutate(_write)

    def map_state(self, state: str, session_id: str) -> None:
        def _write():
            self._data["state_to_sid"][state] = session_id
        self._mutate(_write)

    def pop_state(self, state: str) -> Optional[str]:
        def _write():
            return self._data["state_to_sid"].pop(state, None)
        return self._mutate(_write)

    def get_user_client(self, config_sid: Optional[str]) -> Optional[Dict[str, str]]:
        if not config_sid or self.provider != "figma":
            return None
        with self._lock:
            row = (self._data.get("user_clients") or {}).get(config_sid)
            if isinstance(row, dict) and row.get("client_id"):
                return {
                    "client_id": str(row["client_id"]),
                    "client_secret": str(row.get("client_secret") or ""),
                }
            return None

    def set_user_client(
        self,
        config_sid: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        if self.provider != "figma":
            return

        def _write():
            clients = self._data.setdefault("user_clients", {})
            clients[config_sid] = {
                "client_id": client_id.strip(),
                "client_secret": client_secret.strip(),
                "updated_at": time.time(),
            }
        self._mutate(_write)

    def delete_user_client(self, config_sid: Optional[str]) -> None:
        if not config_sid or self.provider != "figma":
            return

        def _write():
            clients = self._data.get("user_clients")
            if isinstance(clients, dict):
                clients.pop(config_sid, None)
        self._mutate(_write)

    def prune_stale_pending(self, *, max_age_seconds: int = 3600) -> int:
        """清理超时且未拿到 access_token 的半完成授权会话。"""
        now = time.time()

        def _write():
            removed = 0
            sessions: Dict[str, Any] = self._data.get("sessions") or {}
            for sid, session in list(sessions.items()):
                if not isinstance(session, dict):
                    continue
                if session.get("access_token"):
                    continue
                created = float(session.get("created_at") or 0)
                if created and now - created > max_age_seconds:
                    state = session.get("state")
                    if state and self._data["state_to_sid"].get(state) == sid:
                        self._data["state_to_sid"].pop(state, None)
                    sessions.pop(sid, None)
                    removed += 1
            return removed

        return int(self._mutate(_write) or 0)


_supabase_store = OAuthSessionStore("supabase")
_figma_store = OAuthSessionStore("figma")


def get_supabase_oauth_store() -> OAuthSessionStore:
    return _supabase_store


def get_figma_oauth_store() -> OAuthSessionStore:
    return _figma_store


def prune_all_oauth_stores() -> None:
    for store in (_supabase_store, _figma_store):
        removed = store.prune_stale_pending()
        if removed:
            print(f"[OAuthStore:{store.provider}] 清理过期半授权会话 {removed} 个")
