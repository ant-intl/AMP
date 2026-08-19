"""Execution evidence logger for AMP protocol demo.

Provides structured logging that creates a verifiable execution evidence chain.
Every key operation produces a log entry with:
- timestamp
- level (INFO / WARN / ERROR)
- category (state / decision / verify / lifecycle / error / interrupted)
- actor (which role/component)
- action (what happened)
- evidence (concrete data proving the outcome)

Evidence Contract is defined by the Pydantic models in evidence_models.py;
the JSON structure produced by this module is consistent with those Pydantic models.

Output files:
- .logs/execution.jsonl  — full structured log
- .logs/session-summary.json — run verdict with statistics
"""

from __future__ import annotations

import json
import platform
import sys
import time
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class LogEntry:
    """A single execution log entry with evidence."""

    ts: str
    level: str  # INFO | WARN | ERROR
    category: str  # state | decision | verify | lifecycle | error
    actor: str
    action: str
    evidence: dict[str, Any]
    context: dict[str, Any] = field(default_factory=dict)


class ExecutionLogger:
    """Structured execution logger producing verifiable evidence chains.

    Usage:
        logger = ExecutionLogger(log_dir=".logs")
        logger.start_session(mode="auto")
        logger.log_state("ShoppingAgent", "phase_binding_start", {"token_id": None})
        logger.log_decision("ShoppingAgent", "select_product", {"selected": "prod_001", "reason": "first match"})
        logger.log_verify("ShoppingAgent", "verify_l1_l2", passed=True, evidence={"l1": "...", "l2": "..."})
        logger.end_session(verdict="SUCCESS")
    """

    def __init__(self, log_dir: str = ".logs"):
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = open(self._log_dir / "execution.jsonl", "w")
        self._entries: list[LogEntry] = []
        self._verifications: list[dict] = []
        self._run_id = f"run_{uuid.uuid4().hex[:12]}"
        self._start_time: float = 0
        self._session_started = False

    @property
    def run_id(self) -> str:
        return self._run_id

    def start_session(self, mode: str = "auto", **extra_context) -> None:
        """Record session start with environment metadata."""
        self._start_time = time.time()
        self._session_started = True

        self._write_entry(LogEntry(
            ts=self._now(),
            level="INFO",
            category="lifecycle",
            actor="System",
            action="session_start",
            evidence={
                "run_id": self._run_id,
                "mode": mode,
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "argv": sys.argv,
            },
            context=extra_context,
        ))

    def log_state(self, actor: str, action: str, state: dict[str, Any]) -> None:
        """Record a state snapshot (e.g., phase boundary, accumulated tokens)."""
        self._write_entry(LogEntry(
            ts=self._now(),
            level="INFO",
            category="state",
            actor=actor,
            action=action,
            evidence=state,
        ))

    def log_decision(self, actor: str, action: str, evidence: dict[str, Any]) -> None:
        """Record an internal decision with its rationale/data."""
        self._write_entry(LogEntry(
            ts=self._now(),
            level="INFO",
            category="decision",
            actor=actor,
            action=action,
            evidence=evidence,
        ))

    def log_verify(
        self, actor: str, check_name: str, passed: bool, evidence: dict[str, Any]
    ) -> None:
        """Record a verification assertion with pass/fail and evidence."""
        entry = LogEntry(
            ts=self._now(),
            level="INFO" if passed else "ERROR",
            category="verify",
            actor=actor,
            action=check_name,
            evidence={"passed": passed, **evidence},
        )
        self._write_entry(entry)
        self._verifications.append({
            "check": check_name,
            "actor": actor,
            "passed": passed,
            "evidence": evidence,
            "ts": entry.ts,
        })

    def log_error(self, actor: str, action: str, error: str, context: dict[str, Any] | None = None) -> None:
        """Record an error with context. Used for protocol exceptions, Mock Stub faults, and other non-happy-path scenarios."""
        self._write_entry(LogEntry(
            ts=self._now(),
            level="ERROR",
            category="error",
            actor=actor,
            action=action,
            evidence={"error": error},
            context=context or {},
        ))

    def log_interrupted(self, actor: str, action: str, phase_snapshot: dict[str, Any] | None = None) -> None:
        """Record an operator interruption (Ctrl+C / abort).

        Saves the current phase snapshot upon interruption to ensure existing evidence is fully preserved.
        """
        self._write_entry(LogEntry(
            ts=self._now(),
            level="WARN",
            category="interrupted",
            actor=actor,
            action=action,
            evidence={"phase_snapshot": phase_snapshot or {}},
        ))

    def end_session(self, verdict: str, exit_reason: str = "", protocol_event_count: int = 0) -> None:
        """Finalize session, write summary file."""
        end_time = time.time()
        duration_ms = int((end_time - self._start_time) * 1000)

        self._write_entry(LogEntry(
            ts=self._now(),
            level="INFO",
            category="lifecycle",
            actor="System",
            action="session_end",
            evidence={
                "verdict": verdict,
                "exit_reason": exit_reason,
                "duration_ms": duration_ms,
            },
        ))

        # Write session summary
        summary = {
            "run_id": self._run_id,
            "start_time": datetime.fromtimestamp(self._start_time, tz=timezone.utc).isoformat(),
            "end_time": self._now(),
            "duration_ms": duration_ms,
            "python_version": platform.python_version(),
            "mode": next(
                (e.evidence.get("mode") for e in self._entries if e.action == "session_start"),
                "unknown",
            ),
            "total_log_entries": len(self._entries),
            "total_protocol_events": protocol_event_count,
            "verifications": self._verifications,
            "all_checks_passed": all(v["passed"] for v in self._verifications),
            "verdict": verdict,
            "exit_reason": exit_reason,
        }

        summary_path = self._log_dir / "session-summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        self._log_file.close()

    def _write_entry(self, entry: LogEntry) -> None:
        """Write a log entry to file and accumulate."""
        self._entries.append(entry)
        self._log_file.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        self._log_file.flush()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
