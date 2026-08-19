"""ProtocolEvent and EventBus for tracing AMP protocol interactions."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class ProtocolEvent:
    """A single protocol interaction event between two roles."""

    step: int
    phase: str  # "binding" | "mandate" | "checkout"
    from_role: str
    to_role: str
    action: str
    request: dict
    response: dict
    timestamp: str


class EventBus:
    """Collects and outputs ProtocolEvent traces.

    - Prints human-readable summaries to stdout.
    - Writes full JSON Lines to .logs/protocol-events.jsonl.
    """

    def __init__(self, log_dir: str = ".logs"):
        self._step = 0
        self._events: list[ProtocolEvent] = []
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = open(self._log_dir / "protocol-events.jsonl", "w")

    def emit(
        self,
        phase: str,
        from_role: str,
        to_role: str,
        action: str,
        request: dict,
        response: dict,
    ) -> ProtocolEvent:
        """Emit a protocol event: print to stdout and write to jsonl."""
        self._step += 1
        event = ProtocolEvent(
            step=self._step,
            phase=phase,
            from_role=from_role,
            to_role=to_role,
            action=action,
            request=request,
            response=response,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._events.append(event)

        # Human-readable stdout output
        self._print_event(event)

        # JSON Lines file output
        self._log_file.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        self._log_file.flush()

        return event

    def _print_event(self, event: ProtocolEvent) -> None:
        """Print a human-readable event summary to stdout."""
        step_str = f"[Step {event.step:02d}]"
        phase_str = event.phase.ljust(10)
        route_str = f"{event.from_role} → {event.to_role}"
        print(f"  {step_str} {phase_str} | {route_str} | {event.action}")

        # Print compact request/response
        if event.request:
            req_summary = json.dumps(event.request, ensure_ascii=False)
            if len(req_summary) > 120:
                req_summary = req_summary[:117] + "..."
            print(f"           request:  {req_summary}")
        if event.response:
            res_summary = json.dumps(event.response, ensure_ascii=False)
            if len(res_summary) > 120:
                res_summary = res_summary[:117] + "..."
            print(f"           response: {res_summary}")
        print()

    @property
    def events(self) -> list[ProtocolEvent]:
        """All collected events."""
        return list(self._events)

    @property
    def step_count(self) -> int:
        """Current step count."""
        return self._step

    def close(self) -> None:
        """Close the log file handle."""
        self._log_file.close()
