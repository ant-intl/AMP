"""Merchant Service — FastAPI HTTP API.

Provides three merchant-facing endpoints:
  POST /searchProducts  — search the product catalog
  POST /startCheckout   — create a checkout session
  POST /startPayment    — submit a payment to the acquirer

Architecture:
    server.py   : HTTP layer (FastAPI routes + middleware)
    services.py : Business logic (ProductService, CheckoutService, PaymentService)
    repository.py: Data access (SQLite via common.sqlite_store)
    models.py   : Domain models (Product, Checkout, Order, PaymentResult)
    acquirer_client.py: Downstream acquirer HTTP client
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from common.log_config import setup_logging
from common.middleware import HttpLoggingMiddleware

from .models import Item
from .repository import init_db, ProductRepository, CheckoutRepository, OrderRepository
from .services import EventBus, ProductService, CheckoutService, PaymentService
from .acquirer_client import HttpAcquirerClient

logger = setup_logging("merchant")


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------


class SearchProductsRequest(BaseModel):
    """POST /searchProducts request body."""
    query: str = Field(default="", description="Search query string")


class CheckoutItemRequest(BaseModel):
    """Single item in a checkout request."""
    productId: str = Field(..., description="Product ID")
    quantity: int = Field(..., ge=1, description="Quantity (must be >= 1)")


class StartCheckoutRequest(BaseModel):
    """POST /startCheckout request body."""
    items: list[CheckoutItemRequest] = Field(..., description="Cart items")


class StartPaymentRequest(BaseModel):
    """POST /startPayment request body."""
    checkoutId: str = Field(..., description="Checkout ID")
    paymentToken: str = Field(..., description="Payment token from acquirer/CGCP")


# ---------------------------------------------------------------------------
# _AppContext — Dependency injection container
# ---------------------------------------------------------------------------


class _AppContext:
    """Application context: creates and holds all Repository and Service instances."""

    def __init__(self) -> None:
        # Repository
        self.product_repo = ProductRepository()
        self.checkout_repo = CheckoutRepository()
        self.order_repo = OrderRepository()

        # EventBus
        self.event_bus = EventBus()

        # Integration — always use HTTP client (default: localhost:8085)
        acquirer_url = os.environ.get("ACQUIRER_URL", "http://localhost:8085")
        self.acquirer_client = HttpAcquirerClient(acquirer_url)

        # Service
        self.product_service = ProductService(self.product_repo, self.event_bus)
        self.checkout_service = CheckoutService(
            self.product_repo, self.checkout_repo, self.event_bus,
        )
        self.payment_service = PaymentService(
            self.checkout_repo, self.order_repo, self.acquirer_client, self.event_bus,
        )


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Merchant Service",
    description="Merchant demo: product catalog, checkout, and payment via acquirer.",
    version="1.0.0",
)

app.add_middleware(HttpLoggingMiddleware, logger_name="merchant.http")

# Module-level app context, initialized on startup event
_ctx: _AppContext | None = None


@app.on_event("startup")
def _on_startup() -> None:
    """Initialize database and application context."""
    global _ctx
    init_db()
    _ctx = _AppContext()
    logger.info("Merchant application context initialized")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/searchProducts")
def search_products(body: SearchProductsRequest) -> dict[str, Any]:
    """Search the product catalog."""
    query = body.query
    if not query:
        return _error_response("INVALID_PARAM", "query must be a non-empty string")

    products = _ctx.product_service.search(query)

    return {
        "success": True,
        "data": [
            {
                "id": p.id,
                "name": p.name,
                "price": p.price.fetch_minor_units(),
                "currency": p.price.currency_code,
                "imageUrl": p.image_url,
            }
            for p in products
        ],
    }


@app.post("/startCheckout")
def start_checkout(body: StartCheckoutRequest) -> dict[str, Any]:
    """Create a checkout session."""
    if not body.items:
        return _error_response("INVALID_PARAM", "Missing required parameter: items")

    items: list[Item] = [
        Item(product_id=raw.productId, quantity=raw.quantity)
        for raw in body.items
    ]

    try:
        checkout = _ctx.checkout_service.create(items)
    except ValueError as e:
        msg = str(e)
        if msg.startswith("PRODUCT_NOT_FOUND:"):
            return _error_response("PRODUCT_NOT_FOUND", f"Product not found: {msg.split(':')[1]}")
        if msg.startswith("INSUFFICIENT_STOCK:"):
            return _error_response("INSUFFICIENT_STOCK", f"Insufficient stock: {msg.split(':')[1]}")
        return _error_response("INVALID_PARAM", msg)

    return {
        "success": True,
        "data": {
            "checkoutId": checkout.id,
            "items": [{"productId": i.product_id, "quantity": i.quantity} for i in checkout.items],
            "totalAmount": {"cent": checkout.total_amount.fetch_minor_units(), "currency": checkout.total_amount.currency_code},
            "merchantId": checkout.merchant_id,
        },
    }


@app.post("/startPayment")
def start_payment(body: StartPaymentRequest) -> dict[str, Any]:
    """Submit a payment to the acquirer."""
    if not body.checkoutId:
        return _error_response("INVALID_PARAM", "Missing required parameter: checkout_id")
    if not body.paymentToken:
        return _error_response("INVALID_PARAM", "Missing required parameter: payment_token")

    result = _ctx.payment_service.process(body.checkoutId, body.paymentToken)

    if result.success:
        data: dict[str, Any] = {
            "success": True,
            "transactionId": result.transaction_id,
            "message": result.message,
        }
        if result.message and "idempotent" in result.message.lower():
            data["idempotent"] = True
        return {"success": True, "data": data}
    else:
        return {
            "success": False,
            "errorCode": result.error_code,
            "errorMessage": result.message,
        }


@app.get("/health")
def health() -> dict[str, Any]:
    """Health check endpoint."""
    return {"status": "ok", "service": "merchant"}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _error_response(error_code: str, message: str) -> dict[str, Any]:
    """Build an error response dict."""
    return {"success": False, "errorCode": error_code, "errorMessage": message}
