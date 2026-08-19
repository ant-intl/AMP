"""QueryPaymentMethodListAction — Phase 1b: fetch the bound token via CP /queryPaymentMethodList (HTTP)."""

from __future__ import annotations
import logging
from common.http_client import http_post
from orchestrator import AgentState, ActionResult, VerifyEntry

logger = logging.getLogger("shopping-agent")


class QueryPaymentMethodListAction:
    """Phase 1b: query CP /queryPaymentMethodList to obtain the bound token_id.

    Protocol step 4.1: Agent → CP /queryPaymentMethodList.
    Passes the enrollment_session_id from add_payment_method so CP returns
    exactly the payment method produced by this agent's enrollment session.
    Runs on the turn AFTER user completed IDV at MPP (enrollment_idv_pending was set,
    then cleared by server after /idv/confirm succeeded).
    """

    name = "query_payment_method_list"

    def __init__(self, cp_url: str, event_bus, **_kwargs):
        self._cp_url = cp_url
        self._bus = event_bus

    def can_run(self, state: AgentState) -> bool:
        return (
            not state.token_id
            and state.enrollment_requested
            and state.enrollment_idv_done
            and bool(state.enrollment_session_id)
        )

    def execute(self, state: AgentState) -> ActionResult:
        session_id = state.enrollment_session_id or ""

        self._bus.emit(
            phase="binding",
            from_role="Shopping Agent",
            to_role="Credential Provider",
            action="query_payment_method_list",
            request={"session_id": session_id},
            response={},
        )

        r = http_post(
            f"{self._cp_url}/queryPaymentMethodList",
            json={"sessionId": session_id},
            timeout=10,
            logger_name="shopping-agent.http-client",
        )
        r.raise_for_status()
        body = r.json()
        if not body.get("success"):
            raise RuntimeError(f"queryPaymentMethodList failed: {body.get('error', 'unknown')}")

        methods = body.get("paymentMethods") or []
        if not methods:
            raise RuntimeError("queryPaymentMethodList returned success but empty payment_methods")
        method = methods[0]
        token_id = method.get("tokenId", "")
        if not token_id:
            raise RuntimeError("queryPaymentMethodList returned a method without token_id")
        user_login_id = method.get("userLoginId", "")
        wallet_name = method.get("walletName", "")

        self._bus.emit(
            phase="binding",
            from_role="Credential Provider",
            to_role="Shopping Agent",
            action="return_payment_method_list",
            request={},
            response={
                "token_id": token_id,
                "user_login_id": user_login_id,
                "wallet_name": wallet_name,
            },
        )

        logger.info("[Shopping Agent] ✓ Wallet bound — token_id=%s user_login_id=%s", token_id, user_login_id)

        return ActionResult(
            updates={
                "token_id": token_id,
                "enrollment_idv_pending": None,
                "enrollment_idv_done": False,
            },
            verification=VerifyEntry(
                check_name="query_payment_method_list_result",
                passed=True,
                evidence={"session_id": session_id, "token_id": token_id},
            ),
        )
