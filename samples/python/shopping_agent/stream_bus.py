"""EventSink — per-turn event collector, created at turn start and destroyed at turn end.

Bridges the synchronous Agent thread and the async SSE stream:
- The Agent thread writes to a queue.Queue via emit_event()
- The async generator reads from the Queue and yields SSE chunks
- close() sends a termination signal at turn end
"""
from __future__ import annotations

import json
import queue
from typing import Any, Optional


# Sentinel: placed at the tail of the Queue to signal stream end to the async generator
_SENTINEL = None


class EventSink:
    """Per-turn event collector. Thread-safe: written by the Agent thread, read by the async side."""

    def __init__(self) -> None:
        self._queue: queue.Queue = queue.Queue(maxsize=1024)
        self._closed = False

    @property
    def event_queue(self) -> queue.Queue:
        """The Queue from which the async generator reads events."""
        return self._queue

    def emit_event(self, event: dict[str, Any]) -> None:
        """Write an event to the Queue. Called from the Agent thread.

        Events are dropped when the Queue is full (never blocks Agent execution).
        """
        if self._closed:
            return
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            pass  # drop, do not block

    def emit(
        self,
        phase: str,
        from_role: str,
        to_role: str,
        action: str,
        request: dict[str, Any] | None = None,
        response: dict[str, Any] | None = None,
    ) -> None:
        """Compatible with the EventBus.emit() signature for use by the Action layer."""
        self.emit_event({
            "type": "protocol_event",
            "phase": phase,
            "from": from_role,
            "to": to_role,
            "action": action,
            "request": request or {},
            "response": response or {},
        })

    def close(self) -> None:
        """Send the termination signal. The async generator ends the stream upon reading None."""
        if not self._closed:
            self._closed = True
            try:
                self._queue.put_nowait(_SENTINEL)
            except queue.Full:
                pass

    @property
    def closed(self) -> bool:
        return self._closed


def format_sse(event_type: str, data: dict[str, Any]) -> str:
    """Format a single SSE message.

    Args:
        event_type: SSE event field (e.g., "action", "stop")
        data: JSON-serializable data

    Returns:
        SSE-formatted string: "event: xxx\\ndata: {...}\\n\\n"
    """
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
