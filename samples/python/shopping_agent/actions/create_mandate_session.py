"""CreateMandateSessionAction — Phase 2a: create an intent authorization session (HTTP)."""

from __future__ import annotations
import logging
from common.http_client import http_post
from orchestrator import AgentState, ActionResult

logger = logging.getLogger("shopping-agent")


class CreateMandateSessionAction:
    """Phase 2a: create a mandate session via HTTP call to CP /createMandateSession.

    Triggers the full authorization flow (ATS -> MPP -> lib L2 generation -> lib L2 verification).
    Sends the token_id bound in Phase 1 (required by CP) and stores the
    CP-generated session_id for the subsequent inquiry/applyCredential steps.
    Covers protocol step 5.1 (createMandateSession).
    """

    name = "create_mandate_session"

    def __init__(self, cp_url: str, event_bus, identity, interactive_idv: bool = False):
        self._cp_url = cp_url
        self._bus = event_bus
        self._identity = identity
        # Interactive IDV mode: defer mandate verification to a user-confirmed
        # second phase (confirm_mandate_idv). CLI keeps the legacy sync flow.
        self._interactive_idv = interactive_idv

    def can_run(self, state: AgentState) -> bool:
        base = (
            bool(state.token_id)
            and not state.mandate_session_id
            and state.mandate_requested
            and not state.mandate_idv_pending
        )
        if state.scenario == "IMMEDIATE":
            # IMMEDIATE: must have checkout_id first (checkout before mandate)
            return base and bool(state.checkout_id)
        return base

    def execute(self, state: AgentState) -> ActionResult:
        agent_id = self._identity.agent_id
        intent_desc = state.shopping_query or "General shopping"

        # AUTONOMOUS: the agent spends while the user is away, so the mandate
        # must expire when the user said it should. There is no default: the
        # expiry comes from the user's own words (see travel_intent parsing).
        if state.scenario != "IMMEDIATE" and not state.mandate_expire_time:
            raise RuntimeError(
                "createMandateSession requires an expiry time for the "
                "human-not-present flow; ask the user how long the "
                "authorization stays valid."
            )

        self._bus.emit(
            phase="mandate",
            from_role="Shopping Agent",
            to_role="Credential Provider",
            action="create_mandate_session",
            request={"agent_id": agent_id, "token_id": state.token_id, "description": intent_desc},
            response={},
        )

        resp = http_post(
            f"{self._cp_url}/createMandateSession",
            json={
                "agentId": agent_id,
                "tokenId": state.token_id,
                "intentRaw": intent_desc,
                # AUTONOMOUS: the user-stated authorization expiry bounds the
                # mandate (the wallet derives the L2 lifetime from it).
                # IMMEDIATE mandates are single-use, closed right after payment.
                "intentExpireTime": state.mandate_expire_time if state.scenario != "IMMEDIATE" else None,
                "deferIdv": self._interactive_idv,
                "checkout": {
                    "totalAmount": {
                        # round() avoids float-truncation (int(19.99*100)==1998)
                        "cent": round((state.checkout_amount or 0) * 100),
                        "currency": state.checkout_currency or "USD",
                        "value": str(state.checkout_amount or 0),
                    },
                    "merchant": {
                        "referenceMerchantId": state.checkout_merchant_id or "",
                        "merchantName": "Demo Store",
                        "merchantMcc": "5411",
                    },
                } if state.scenario == "IMMEDIATE" else None,
                # AUTONOMOUS: propagate the user-stated budget into the mandate
                # constraints so the authorization reflects the user's intent
                # (e.g. "under $150") instead of the CP's demo default. The CP
                # does not merge partial constraints with its defaults, so the
                # full constraint set is sent; the merchant list matches the
                # demo checkout. Never sent for IMMEDIATE: a constraints field
                # alongside checkout would flip the CP's mandate-type detection.
                "constraints": {
                    "budgetAmount": {
                        "cent": round((state.budget_max or 0) * 100),
                        "currency": "USD",
                        "value": f"{state.budget_max:.2f}",
                    },
                    "merchantNameList": ["Demo Store"],
                    "merchantMccList": ["5411"],
                } if state.scenario != "IMMEDIATE" and state.budget_max else None,
            },
            timeout=10,
            logger_name="shopping-agent.http-client",
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            raise RuntimeError(f"createMandateSession failed: {body.get('error', 'unknown')}")

        mandate_session_id = body.get("sessionId", "")
        if not mandate_session_id:
            raise RuntimeError("createMandateSession returned success but no session_id")

        self._bus.emit(
            phase="mandate",
            from_role="Credential Provider",
            to_role="Shopping Agent",
            action="return_mandate_session_id",
            request={},
            response={"session_id": mandate_session_id},
        )

        # Interactive mode: IDV session created; pause the turn for user
        # confirmation at MPP. The next turn resumes with inquiry_mandate_session.
        if body.get("status") == "PENDING_IDV":
            idv = body.get("idv") or {}
            auth_session_id = idv.get("authSessionId", "")
            if not auth_session_id:
                raise RuntimeError("createMandateSession PENDING_IDV but no idv.authSessionId")
            logger.debug("[Shopping Agent] IDV pending (mandate) — session_id=%s", mandate_session_id)
            return ActionResult(
                updates={
                    "mandate_session_id": mandate_session_id,
                    "mandate_idv_pending": auth_session_id,
                    # Clear any stale confirm so the next phase truly waits (R2)
                    "user_confirmed": False,
                }
            )

        logger.info("[Shopping Agent] ✓ Mandate session created — session_id=%s", mandate_session_id)

        return ActionResult(updates={"mandate_session_id": mandate_session_id})
