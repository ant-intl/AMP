from __future__ import annotations

import json
import uuid
import logging
import pathlib
import sys
from datetime import datetime, timezone
from typing import Callable, Protocol

_project_root = pathlib.Path(__file__).resolve().parents[3]
_src_python = str(_project_root / "src" / "python")
if _src_python not in sys.path:
    sys.path.insert(0, _src_python)

from common.multi_currency_money import MultiCurrencyMoney
from .models import (
    Product, Item, Checkout,
    PaymentResult, AcquirerPaymentResponse, Order,
)
from .repository import ProductRepository, CheckoutRepository, OrderRepository


# ---------------------------------------------------------------------------
# EventBus — Synchronous event publish/subscribe
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)


class EventBus:
    """Synchronous event bus supporting publish / subscribe."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable]] = {}
        # Register default logging handler
        self.subscribe("*", self._default_log_handler)

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def publish(self, event_type: str, payload: dict) -> None:
        """Publish an event (synchronously invokes all subscribers)."""
        # Invoke exact-match handlers
        for handler in self._handlers.get(event_type, []):
            handler(event_type, payload)
        # Invoke wildcard handlers
        for handler in self._handlers.get("*", []):
            handler(event_type, payload)

    @staticmethod
    def _default_log_handler(event_type: str, payload: dict) -> None:
        """Default logging handler — audit output."""
        logger.info("[EVENT] %s | %s", event_type, payload)


# ---------------------------------------------------------------------------
# ProductService — Product search business logic
# ---------------------------------------------------------------------------


class ProductService:
    """Product catalog service."""

    def __init__(self, product_repo: ProductRepository, event_bus: EventBus) -> None:
        self._product_repo = product_repo
        self._event_bus = event_bus

    def search(self, query: str) -> list[Product]:
        """
        Search product catalog.
        Empty or "*" query → return all; otherwise match keywords against name + description.
        """
        if not query or query.strip() == "*":
            internals = self._product_repo.list_all()
        else:
            keywords = query.lower().split()
            internals = self._product_repo.search(keywords)

        self._event_bus.publish("catalog.searched", {"query": query, "results": len(internals)})
        return internals


# ---------------------------------------------------------------------------
# CheckoutService — Checkout business logic
# ---------------------------------------------------------------------------

MERCHANT_ID = "MERCHANT-DEMO-001"


class CheckoutService:
    """Checkout service."""

    def __init__(
        self,
        product_repo: ProductRepository,
        checkout_repo: CheckoutRepository,
        event_bus: EventBus,
    ) -> None:
        self._product_repo = product_repo
        self._checkout_repo = checkout_repo
        self._event_bus = event_bus

    def create(self, items: list[Item]) -> Checkout:
        """
        Create a checkout session:
        1. Validate product_id exists and stock is sufficient
        2. Calculate total_amount
        3. Generate checkout_id
        4. Publish checkout.created event
        """
        total_amount_cents = 0
        currency = "USD"

        for item in items:
            product = self._product_repo.find_by_id(item.product_id)
            if product is None:
                raise ValueError(f"PRODUCT_NOT_FOUND:{item.product_id}")
            if product.stock < item.quantity:
                raise ValueError(f"INSUFFICIENT_STOCK:{item.product_id}")
            total_amount_cents += product.price.fetch_minor_units() * item.quantity
            currency = product.price.currency_code

        # Generate ID
        checkout_id = f"CKO-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc).isoformat()

        # Serialize items
        items_json = json.dumps([{"product_id": i.product_id, "quantity": i.quantity} for i in items])

        # Save Checkout
        self._checkout_repo.save(
            checkout_id=checkout_id,
            items_json=items_json,
            total_amount=total_amount_cents,
            currency=currency,
            merchant_id=MERCHANT_ID,
            created_at=now,
        )

        # Publish event
        self._event_bus.publish("checkout.created", {
            "checkout_id": checkout_id,
            "total_amount": total_amount_cents,
        })

        # Return external model
        return Checkout(
            id=checkout_id,
            items=items,
            total_amount=MultiCurrencyMoney.of(total_amount_cents, currency),
            merchant_id=MERCHANT_ID,
        )


# ---------------------------------------------------------------------------
# AcquirerClient Protocol (dependency for PaymentService)
# ---------------------------------------------------------------------------


class AcquirerClient(Protocol):
    def submit_payment(
        self, *, checkout_id: str, amount: MultiCurrencyMoney, payment_token: str, merchant_id: str
    ) -> AcquirerPaymentResponse: ...


# ---------------------------------------------------------------------------
# PaymentService — Payment business logic
# ---------------------------------------------------------------------------


class PaymentService:
    """Payment service."""

    def __init__(
        self,
        checkout_repo: CheckoutRepository,
        order_repo: OrderRepository,
        acquirer_client: AcquirerClient,
        event_bus: EventBus,
    ) -> None:
        self._checkout_repo = checkout_repo
        self._order_repo = order_repo
        self._acquirer_client = acquirer_client
        self._event_bus = event_bus

    def process(self, checkout_id: str, payment_token: str) -> PaymentResult:
        """Process payment: idempotency check → validate checkout → call acquirer → record order → return result."""

        # 1. Idempotency check: has this checkout already been paid successfully?
        existing_order = self._order_repo.find_success_by_checkout_id(checkout_id)
        if existing_order is not None:
            return PaymentResult(
                success=True,
                transaction_id=existing_order.acquirer_transaction_id,
                message="Payment already completed (idempotent)",
            )

        # 2. Validate checkout exists
        checkout_data = self._checkout_repo.find_by_id(checkout_id)
        if checkout_data is None:
            return PaymentResult(
                success=False,
                transaction_id="",
                message=f"Checkout not found: {checkout_id}",
                error_code="CHECKOUT_NOT_FOUND",
            )

        # 3. Publish event
        self._event_bus.publish("payment.submitted", {
            "checkout_id": checkout_id,
            "payment_token": payment_token,
            "amount": checkout_data["total_amount"],
        })

        # 4. Call acquirer
        now = datetime.now(timezone.utc).isoformat()
        checkout_amount: MultiCurrencyMoney = checkout_data["total_amount"]
        try:
            acq_response = self._acquirer_client.submit_payment(
                checkout_id=checkout_id,
                amount=checkout_amount,
                payment_token=payment_token,
                merchant_id=checkout_data.get("merchant_id", MERCHANT_ID),
            )
        except Exception as exc:
            logger.exception("Acquirer call failed for checkout %s", checkout_id)
            # Record failed order on exception
            order = Order(
                order_id=f"ORD-{uuid.uuid4().hex[:8].upper()}",
                checkout_id=checkout_id,
                payment_token=payment_token,
                status="FAILED",
                acquirer_transaction_id="",
                created_at=now,
            )
            self._order_repo.save(order)
            self._event_bus.publish("payment.completed", {
                "checkout_id": checkout_id,
                "success": False,
            })
            return PaymentResult(
                success=False,
                transaction_id="",
                message="Acquirer call failed",
                error_code="ACQUIRER_FAILED",
            )

        # 5. Record order
        order = Order(
            order_id=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            checkout_id=checkout_id,
            payment_token=payment_token,
            status="SUCCESS" if acq_response.success else "FAILED",
            acquirer_transaction_id=acq_response.acquirer_payment_id if acq_response.success else "",
            created_at=now,
        )
        self._order_repo.save(order)

        # 6. Publish event
        self._event_bus.publish("payment.completed", {
            "checkout_id": checkout_id,
            "order_id": order.order_id,
            "success": acq_response.success,
            "transaction_id": order.acquirer_transaction_id,
        })

        # 7. Return result
        if acq_response.success:
            return PaymentResult(
                success=True,
                transaction_id=acq_response.acquirer_payment_id,
                message="Payment processed successfully",
            )
        else:
            return PaymentResult(
                success=False,
                transaction_id="",
                message=acq_response.message,
                error_code="ACQUIRER_FAILED",
            )
