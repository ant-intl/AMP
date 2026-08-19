"""StartPaymentAction — Phase 3.5: submit the payment token to complete payment (HTTP)."""

from __future__ import annotations
import logging
from common.http_client import http_post
from orchestrator import AgentState, ActionResult, VerifyEntry

logger = logging.getLogger("shopping-agent")


class StartPaymentAction:
    """Phase 3.5: complete payment via HTTP call to Merchant /startPayment.

    The Merchant routes the request to Acquirer -> AlipayPlus -> MPP for settlement.
    Covers protocol step 15 (/startPayment).
    """

    name = "start_payment"

    def __init__(self, merchant_url: str, event_bus, **_kwargs):
        self._merchant_url = merchant_url
        self._bus = event_bus

    def can_run(self, state: AgentState) -> bool:
        return bool(state.payment_token) and not state.paid

    def execute(self, state: AgentState) -> ActionResult:
        self._bus.emit(
            phase="checkout",
            from_role="Shopping Agent",
            to_role="Merchant",
            action="start_payment",
            request={"checkout_id": state.checkout_id, "payment_token": state.payment_token},
            response={},
        )

        resp = http_post(
            f"{self._merchant_url}/startPayment",
            json={
                "checkoutId": state.checkout_id or "",
                "paymentToken": state.payment_token or "",
            },
            logger_name="shopping-agent.http-client",
        )
        resp.raise_for_status()
        result = resp.json()

        # Merchant wraps response as {"success": bool, "data": {...}} or flat format
        if "data" in result:
            inner = result["data"]
            success = inner.get("success", result.get("success", False))
            transaction_id = inner.get("transactionId", "")
            message = inner.get("message", "")
        else:
            success = result.get("success", False)
            transaction_id = result.get("transactionId", "")
            message = result.get("message", "")

        if success:
            logger.info("[Shopping Agent] ✓ Payment Success — transaction_id=%s", transaction_id)
        else:
            logger.warning("[Shopping Agent] ✗ Payment Failed — %s", message)

        return ActionResult(
            updates=self._build_updates(state, success, transaction_id),
            verification=VerifyEntry(
                check_name="payment_result",
                passed=success,
                evidence={"transaction_id": transaction_id, "message": message},
            ),
        )

    def _build_updates(self, state: AgentState, success: bool, transaction_id: str) -> dict:
        """Build state updates; drives multi-item loop when purchase_queue is active."""
        updates: dict = {"paid": success, "transaction_id": transaction_id}
        if not success:
            return updates

        queue = list(getattr(state, "purchase_queue", None) or [])
        if not queue:
            return updates

        # Multi-item: record purchase, deduct budget, advance queue
        product = state.selected_product or {}
        raw_price = product.get("price", 0) or 0
        # Handle both int (cents) and dict ({"cent": N} or {"value": N}) formats
        if isinstance(raw_price, dict):
            price_cents = raw_price.get("cent") or raw_price.get("value") or 0
        else:
            price_cents = raw_price
        price_dollars = price_cents / 100
        spent = (getattr(state, "spent_total", 0.0) or 0.0) + price_dollars
        purchased = list(getattr(state, "purchased_items", None) or [])
        purchased.append({
            "name": product.get("name", ""),
            "price": price_dollars,
            "service": queue[0],
        })

        remaining_queue = queue[1:]
        updates.update({
            "spent_total": spent,
            "purchased_items": purchased,
            "purchase_queue": remaining_queue,
            # Reset intermediate state for next iteration
            "products": [],
            "selected_product": None,
            "checkout_id": None,
            "checkout_amount": None,
            "l3_serialized": None,
            "payment_token": None,
            "paid": False if remaining_queue else True,
            "match_reasons": [],
        })
        return updates
