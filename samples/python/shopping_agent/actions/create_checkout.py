"""CreateCheckoutAction — Phase 3.2: create a checkout session (HTTP)."""

from __future__ import annotations
import logging
from common.http_client import http_post
from orchestrator import AgentState, ActionResult

logger = logging.getLogger("shopping-agent")


class CreateCheckoutAction:
    """Phase 3.2: create a checkout via HTTP call to Merchant /startCheckout, generating a checkout ID and amount."""

    name = "create_checkout"

    def __init__(self, merchant_url: str, event_bus, **_kwargs):
        self._merchant_url = merchant_url
        self._bus = event_bus

    def can_run(self, state: AgentState) -> bool:
        return state.selected_product is not None and not state.checkout_id

    def execute(self, state: AgentState) -> ActionResult:
        product = state.selected_product
        items = [{"productId": product["id"], "quantity": 1}]

        resp = http_post(
            f"{self._merchant_url}/startCheckout",
            json={"items": items},
            timeout=10,
            logger_name="shopping-agent.http-client",
        )
        resp.raise_for_status()
        body = resp.json()

        # Check for wrapped error response
        if "success" in body and not body["success"]:
            error_msg = body.get("errorMessage") or body.get("error") or "unknown"
            raise RuntimeError(f"startCheckout failed: {error_msg}")

        # Support both flat and wrapped response formats
        data = body.get("data", body)
        checkout_id = data.get("checkoutId") or data.get("id", "")
        # Merchant amounts are minor units (cents); the Agent state and all
        # downstream consumers (mandate cent/value, L3, receipt) use USD.
        raw_amount = data.get("totalAmount") or 0
        # Handle both int (cents) and dict ({"cent": N}) formats
        if isinstance(raw_amount, dict):
            amount_cents = raw_amount.get("cent") or raw_amount.get("value") or 0
        else:
            amount_cents = raw_amount
        total_amount = amount_cents / 100
        currency = data.get("currency", "")
        merchant_id = data.get("merchantId", "")
        if not checkout_id:
            raise RuntimeError("startCheckout returned no checkout id")

        self._bus.emit(
            phase="checkout",
            from_role="Merchant",
            to_role="Shopping Agent",
            action="return_checkout",
            request={},
            response={
                "checkout_id": checkout_id,
                "total_amount": total_amount,
                "currency": currency,
            },
        )

        logger.info("[Shopping Agent] ✓ Checkout created — id=%s, amount=$%s", checkout_id, total_amount)

        return ActionResult(
            updates={
                "checkout_id": checkout_id,
                "checkout_amount": total_amount,
                "checkout_currency": currency,
                "checkout_merchant_id": merchant_id,
            },
        )
