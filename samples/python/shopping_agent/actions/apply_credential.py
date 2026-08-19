"""ApplyCredentialAction — Phase 3.4: submit L1+L2+L3 to obtain a payment token (HTTP)."""

from __future__ import annotations
import logging
from common.http_client import http_post
from orchestrator import AgentState, ActionResult

logger = logging.getLogger("shopping-agent")

# Maximum characters shown in event-bus log previews
_LOG_PREVIEW_LENGTH = 20


class ApplyCredentialAction:
    """Phase 3.4: obtain a payment token via HTTP call to CP /applyCredential.

    Submits the mandate session_id + L1 & L2 & L3 packets; CP resolves
    token_id/mandate_id from its session record and forwards the request to
    AlipayPlus for three-layer authorization chain verification.
    Covers protocol step 14 (/applyCredential with L1 & L2 & L3).
    """

    name = "apply_credential"

    def __init__(self, cp_url: str, event_bus, **_kwargs):
        self._cp_url = cp_url
        self._bus = event_bus

    def can_run(self, state: AgentState) -> bool:
        if state.scenario == "IMMEDIATE":
            # IMMEDIATE: L2 is enough (no L3 needed)
            return bool(state.l2_serialized) and not state.payment_token
        # AUTONOMOUS: requires L3
        return state.l3_serialized is not None and not state.payment_token

    def execute(self, state: AgentState) -> ActionResult:
        # Build checkout for applyCredential (required for both IMMEDIATE and AUTONOMOUS)
        # IMMEDIATE: checkout must match createAuthorization checkout (hash comparison)
        # AUTONOMOUS: checkout must satisfy mandate constraints (merchant + budget)
        checkout = None
        if state.checkout_amount:
            checkout = {
                "totalAmount": {
                    "cent": round((state.checkout_amount or 0) * 100),
                    "currency": state.checkout_currency or "USD",
                    "value": str(state.checkout_amount or 0),
                },
                "merchant": {
                    "referenceMerchantId": state.checkout_merchant_id or "",
                    "merchantName": state.checkout_merchant_name,
                    "merchantMcc": state.checkout_merchant_mcc,
                },
            }

        self._bus.emit(
            phase="checkout",
            from_role="Shopping Agent",
            to_role="Credential Provider",
            action="apply_credential",
            request={
                "session_id": state.mandate_session_id,
                "l1": (state.l1_serialized or "")[:_LOG_PREVIEW_LENGTH] + "...",
                "l2": (state.l2_serialized or "")[:_LOG_PREVIEW_LENGTH] + "...",
                "l3": (state.l3_serialized or "")[:_LOG_PREVIEW_LENGTH] + "...",
                "checkout": checkout,
            },
            response={},
        )

        payload: dict = {
            "sessionId": state.mandate_session_id or "",
            "l1Serialized": state.l1_serialized or "",
            "l2Serialized": state.l2_serialized or "",
            "l3Serialized": state.l3_serialized or "",
        }
        if checkout:
            payload["checkout"] = checkout

        resp = http_post(
            f"{self._cp_url}/applyCredential",
            json=payload,
            logger_name="shopping-agent.http-client",
        )
        resp.raise_for_status()
        body = resp.json()

        if not body.get("success"):
            error_msg = body.get("error") or body.get("resultMessage") or "Unknown error from CP"
            raise RuntimeError(f"applyCredential failed: {error_msg}")

        payment_token = body.get("paymentToken", "")
        if not payment_token:
            raise RuntimeError("applyCredential returned success but no payment_token")

        self._bus.emit(
            phase="checkout",
            from_role="Credential Provider",
            to_role="Shopping Agent",
            action="return_payment_token",
            request={},
            response={"payment_token": payment_token},
        )

        logger.info("[Shopping Agent] ✓ Payment token received — token=%s", payment_token)

        return ActionResult(updates={"payment_token": payment_token})
