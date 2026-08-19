"""TaskSession — session management for multi-turn conversations.

Each task_id corresponds to one TaskSession, persisted across turns:
- state: AgentState (protocol state)
- agent: ShoppingAgent instance (includes keys, Registry, Planner)
- conversation: conversation history
- status: task status
- evidence: accumulated Evidence events
- lock: asyncio.Lock (per-task concurrency guard)
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskSession:
    """Session state for a single task."""

    task_id: str
    agent: Any  # ShoppingAgent instance
    state: Any  # AgentState reference (Runtime._state)
    conversation: list[dict[str, Any]] = field(default_factory=list)
    status: str = "idle"  # idle / running / waiting / completed / failed
    evidence: list[dict[str, Any]] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def add_message(self, role: str, text: str, **extra: Any) -> None:
        """Append a conversation message."""
        msg = {"role": role, "text": text, **extra}
        self.conversation.append(msg)

    def add_evidence(self, event: dict[str, Any]) -> None:
        """Append an Evidence event."""
        self.evidence.append(event)


# Process-level session storage (in-memory only; no disk persistence)
_sessions: dict[str, TaskSession] = {}


def get_session(task_id: str) -> TaskSession | None:
    return _sessions.get(task_id)


def register_session(session: TaskSession) -> None:
    _sessions[session.task_id] = session


def remove_session(task_id: str) -> None:
    _sessions.pop(task_id, None)


def list_sessions() -> list[str]:
    return list(_sessions.keys())
