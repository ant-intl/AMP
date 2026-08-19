"""Thread-safe in-memory session and token store for MPP."""

from __future__ import annotations

import threading
from typing import Any


class MppStore:
    """Thread-safe in-memory store for IDV sessions and payment tokens."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._payment_tokens: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def put_session(self, session_id: str, session: dict[str, Any]) -> None:
        with self._lock:
            self._sessions[session_id] = session

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._lock:
            s = self._sessions.get(session_id)
            return dict(s) if s else None

    def update_session(self, session_id: str, **fields: Any) -> None:
        with self._lock:
            s = self._sessions.get(session_id)
            if s is not None:
                s.update(fields)

    def get_payment_token(self, token: str) -> dict[str, Any] | None:
        with self._lock:
            r = self._payment_tokens.get(token)
            return dict(r) if r else None

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._payment_tokens.clear()

    def snapshot_sessions(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {
                k: {
                    "authId": v.get("auth_id"),
                    "status": v.get("status"),
                    "authContext": v.get("auth_context"),
                    "mandateType": v.get("mandate_type"),
                    "createdAt": v.get("created_at"),
                }
                for k, v in self._sessions.items()
            }
