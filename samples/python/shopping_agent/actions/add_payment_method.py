"""AddPaymentMethodAction — Phase 1: initiate wallet binding via CP /addPaymentMethod (HTTP)."""

from __future__ import annotations
import logging
from common.http_client import http_post
from orchestrator import AgentState, ActionResult, VerifyEntry

logger = logging.getLogger("shopping-agent")


class AddPaymentMethodAction:
    """Phase 1: initiate wallet binding via CP /credential-provider/addPaymentMethod.

    Protocol step 1.1: Agent → CP /credential-provider/addPaymentMethod.
    CP returns {session_id, status}; the session_id is the contract key for
    the follow-up /queryPaymentMethodList call.
    CP blocks until IDV callback completes (status=COMPLETED); then Agent
    immediately queries /queryPaymentMethodList in the same action.
    """

    name = "add_payment_method"

    def __init__(self, cp_url: str, event_bus, identity, interactive_idv: bool = False, **_kwargs):
        self._cp_url = cp_url
        self._bus = event_bus
        self._identity = identity
        self._interactive_idv = interactive_idv

    def can_run(self, state: AgentState) -> bool:
        return (
            not state.token_id
            and state.enrollment_requested
            and not state.enrollment_idv_pending
            and not state.enrollment_idv_done
        )

    def execute(self, state: AgentState) -> ActionResult:
        self._bus.emit(
            phase="binding",
            from_role="Shopping Agent",
            to_role="Credential Provider",
            action="add_payment_method",
            request={"agent_id": self._identity.agent_id},
            response={},
        )

        # Step 1.1: trigger binding flow
        r = http_post(
            f"{self._cp_url}/addPaymentMethod",
            json={"agentId": self._identity.agent_id, "walletName": "ALIPAY_HK"},
            timeout=30,
            logger_name="shopping-agent.http-client",
        )
        r.raise_for_status()
        body = r.json()
        if not body.get("success"):
            raise RuntimeError(f"addPaymentMethod failed: {body.get('error', 'unknown')}")

        session_id = body.get("sessionId", "")
        if not session_id:
            raise RuntimeError("addPaymentMethod returned success but no session_id")

        # Web mode: IDV session created; pause the turn for user
        # confirmation at MPP. The next turn resumes with query_payment_method_list.
        if body.get("status") == "PENDING_IDV":
            idv = body.get("idv") or {}
            auth_session_id = idv.get("authSessionId", "")
            if not auth_session_id:
                raise RuntimeError("addPaymentMethod PENDING_IDV but no idv.authSessionId")
            logger.info("[Shopping Agent] >> IDV pending (enrollment). session_id=%s", session_id)
            return ActionResult(
                updates={
                    "enrollment_session_id": session_id,
                    "enrollment_idv_pending": auth_session_id,
                },
            )

        # CLI mode: CP blocks until callback; query token immediately.
        return self._query_token(session_id)

    def _query_token(self, session_id: str) -> ActionResult:
        """Step 4.1: query payment method list by session_id to obtain token_id."""
        self._bus.emit(
            phase="binding",
            from_role="Shopping Agent",
            to_role="Credential Provider",
            action="query_payment_method_list",
            request={"session_id": session_id},
            response={},
        )
        r2 = http_post(
            f"{self._cp_url}/queryPaymentMethodList",
            json={"sessionId": session_id},
            timeout=10,
            logger_name="shopping-agent.http-client",
        )
        r2.raise_for_status()
        body2 = r2.json()
        if not body2.get("success"):
            raise RuntimeError(f"queryPaymentMethodList failed: {body2.get('error', 'unknown')}")

        methods = body2.get("paymentMethods") or []
        if not methods:
            raise RuntimeError("queryPaymentMethodList returned success but empty payment_methods")
        token_id = methods[0].get("tokenId", "")
        if not token_id:
            raise RuntimeError("queryPaymentMethodList returned a method without token_id")

        self._bus.emit(
            phase="binding",
            from_role="Credential Provider",
            to_role="Shopping Agent",
            action="return_payment_method_list",
            request={},
            response={"token_id": token_id},
        )

        logger.info("[Shopping Agent] ✓ Wallet bound — token_id=%s", token_id)

        return ActionResult(
            updates={
                "enrollment_session_id": session_id,
                "token_id": token_id,
                "enrollment_idv_pending": None,
            },
            verification=VerifyEntry(
                check_name="add_payment_method_result",
                passed=True,
                evidence={"session_id": session_id, "token_id": token_id},
            ),
        )
