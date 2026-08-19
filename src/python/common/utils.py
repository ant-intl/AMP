"""Common utility functions shared across all modules.

Provides:
  - ``gen_id()`` — generate a 32-char hex identifier (UUID4 without hyphens).
  - ``short_id(prefix, length)`` — generate a short prefixed identifier.
  - ``generate_agent_id()`` — generate a demo agent identifier (``agent-XXXXXX``).
"""

from __future__ import annotations

import uuid


def gen_id() -> str:
    """Return a 32-character hex string (UUID4 with hyphens removed)."""
    return str(uuid.uuid4()).replace("-", "")


def short_id(prefix: str = "", length: int = 6) -> str:
    """Return a short hex string, optionally prefixed.

    Example: ``short_id("agent-", 6)`` → ``"agent-a1b2c3"``
    """
    return f"{prefix}{uuid.uuid4().hex[:length]}"


def generate_agent_id() -> str:
    """Generate a demo agent identifier: ``agent-XXXXXX``."""
    return short_id("agent-", 6)
