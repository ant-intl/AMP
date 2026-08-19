from __future__ import annotations

import pathlib, sys
from dataclasses import dataclass

_project_root = pathlib.Path(__file__).resolve().parents[3]
_src_python = str(_project_root / "src" / "python")
if _src_python not in sys.path:
    sys.path.insert(0, _src_python)

from common.multi_currency_money import MultiCurrencyMoney


# ---------------------------------------------------------------------------
# Product — Product model
# ---------------------------------------------------------------------------


@dataclass
class Product:
    id: str  # Product ID
    name: str  # Product name
    description: str  # Product description
    price: MultiCurrencyMoney  # Price
    stock: int  # Stock quantity
    image_url: str  # Product image URL

    def __repr__(self) -> str:
        return (
            f"Product(id={self.id!r}, name={self.name!r}, "
            f"price={self.price}, stock={self.stock})"
        )


# ---------------------------------------------------------------------------
# Checkout — Checkout model
# ---------------------------------------------------------------------------


@dataclass
class Item:
    product_id: str  # Product ID
    quantity: int  # Quantity


@dataclass
class Checkout:
    id: str  # Checkout ID
    items: list[Item]  # Cart item list
    total_amount: MultiCurrencyMoney  # Total amount
    merchant_id: str  # Merchant ID (Acquirer looks up merchant details)

    def __repr__(self) -> str:
        return (
            f"Checkout(id={self.id!r}, items={self.items!r}, "
            f"total_amount={self.total_amount}, "
            f"merchant_id={self.merchant_id!r})"
        )


# ---------------------------------------------------------------------------
# Order (payment record)
# ---------------------------------------------------------------------------


@dataclass
class Order:
    order_id: str         # Order ID
    checkout_id: str      # Associated checkout
    payment_token: str    # Payment token used
    status: str           # SUCCESS / FAILED
    acquirer_transaction_id: str  # Acquirer transaction ID
    created_at: str       # Creation time (ISO8601)

    def __repr__(self) -> str:
        return (
            f"Order(order_id={self.order_id!r}, checkout_id={self.checkout_id!r}, "
            f"status={self.status!r})"
        )


# ---------------------------------------------------------------------------
# Payment — Payment model
# ---------------------------------------------------------------------------


@dataclass
class PaymentResult:
    success: bool  # Whether successful
    transaction_id: str  # Transaction ID
    message: str  # Result description
    error_code: str = ""  # Error code (e.g. CHECKOUT_NOT_FOUND, ACQUIRER_FAILED)

    def __repr__(self) -> str:
        return (
            f"PaymentResult(success={self.success}, "
            f"transaction_id={self.transaction_id!r}, "
            f"message={self.message!r})"
        )


@dataclass
class AcquirerPaymentResponse:
    success: bool  # Whether acquirer succeeded
    acquirer_payment_id: str  # Acquirer payment ID
    message: str  # Description
