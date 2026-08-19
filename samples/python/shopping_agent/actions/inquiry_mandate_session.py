"""InquiryMandateSessionAction — Phase 2b: query the mandate session to obtain L1 & L2 (HTTP)."""

from __future__ import annotations
import logging
from typing import Any
from common.http_client import http_post
from orchestrator import AgentState, ActionResult, VerifyEntry

logger = logging.getLogger("shopping-agent")


class InquiryMandateSessionAction:
    """Phase 2b: obtain L1, L2, and mandate_id via HTTP call to CP /inquiryMandateSession.

    Queries strictly by the CP session_id returned by create_mandate_session.
    Covers protocol step 9 (inquiryMandateSession).
    """

    name = "inquiry_mandate_session"

    def __init__(self, cp_url: str, event_bus, **_kwargs):
        self._cp_url = cp_url
        self._bus = event_bus

    def can_run(self, state: AgentState) -> bool:
        return (
            bool(state.mandate_session_id)
            and not state.l1_serialized
            and not state.mandate_idv_pending
        )

    def execute(self, state: AgentState) -> ActionResult:
        session_id = state.mandate_session_id or ""

        self._bus.emit(
            phase="mandate",
            from_role="Shopping Agent",
            to_role="Credential Provider",
            action="inquiry_mandate_session",
            request={"session_id": session_id},
            response={},
        )

        resp = http_post(
            f"{self._cp_url}/inquiryMandateSession",
            json={"sessionId": session_id},
            timeout=10,
            logger_name="shopping-agent.http-client",
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(f"inquiryMandateSession failed: {data.get('error', 'unknown')}")
        if data.get("status") != "COMPLETED":
            raise RuntimeError(
                f"inquiryMandateSession: session {session_id} is {data.get('status')}, not COMPLETED")

        l1_serialized = data.get("l1Serialized", "")
        l2_serialized = data.get("l2Serialized", "")
        mandate_id = data.get("mandateId", "")
        if not l1_serialized or not l2_serialized or not mandate_id:
            raise RuntimeError("inquiryMandateSession returned success but missing l1/l2/mandate_id")

        self._bus.emit(
            phase="mandate",
            from_role="Credential Provider",
            to_role="Shopping Agent",
            action="return_l1_l2",
            request={},
            response={
                "mandate_id": mandate_id,
                "l1_serialized": l1_serialized[:30] + "...",
                "l2_serialized": l2_serialized[:30] + "...",
            },
        )

        logger.info("[Shopping Agent] ✓ Mandate inquiry done — mandate_id=%s", mandate_id)

        updates: dict[str, Any] = {
            "mandate_id": mandate_id,
            "l1_serialized": l1_serialized,
            "l2_serialized": l2_serialized,
        }
        # Auto-resume: if the user already expressed a purchase intent before
        # the mandate completed, resume the purchase flow without requiring a
        # second "buy X" turn. Guarded to non-IMMEDIATE so the human-present
        # single-use flow is untouched.
        if state.shopping_query and state.scenario != "IMMEDIATE":
            updates["purchase_requested"] = True

        return ActionResult(
            updates=updates,
            verification=VerifyEntry(
                check_name="inquiry_mandate_session_result",
                passed=True,
                evidence={
                    "session_id": session_id,
                    "mandate_id": mandate_id,
                    "l1_serialized_len": len(l1_serialized),
                    "l2_serialized_len": len(l2_serialized),
                },
            ),
        )
