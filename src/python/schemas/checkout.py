"""Checkout domain model."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from common.multi_currency_money import MultiCurrencyMoney


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class CheckoutExtendType(str, Enum):
    """
    Enum for checkout ext_info field keys.

    Centralizes all extension field keys used in checkout ext_info
    to avoid scattered string literals.
    """

    REFERENCE_CHECKOUT_ID = "referenceCheckoutId"  # Associated TR checkout ID
    SOURCE_AMOUNT = "SOURCE_AMOUNT"  # Source amount
    QUOTE_RESULT = "QUOTE_RESULT"  # FX quote result

    @classmethod
    def get_by_code(cls, code: str) -> Optional["CheckoutExtendType"]:
        """Get enum member by code, return None if not found."""
        if not code:
            return None
        for member in cls:
            if member.value == code:
                return member
        return None


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass
class Merchant:
    """
    Merchant information value object.
    """

    reference_merchant_id: Optional[str] = None  # Merchant ID
    merchant_name: Optional[str] = None  # Merchant name
    merchant_mcc: Optional[str] = None  # Merchant MCC
    merchant_web_site_url: Optional[str] = None  # Merchant URL
    store_name: Optional[str] = None  # Store name

    def __repr__(self) -> str:
        return (
            f"Merchant(reference_merchant_id={self.reference_merchant_id!r}, "
            f"merchant_name={self.merchant_name!r}, "
            f"store_name={self.store_name!r})"
        )


@dataclass
class CartInfo:
    """
    Cart information value object.

    Encapsulates checkout cart data including total amount, item list, etc.
    """

    total_amount: Optional[MultiCurrencyMoney] = None  # Total amount
    item_count: Optional[int] = None  # Item count
    items: Optional[str] = None  # Item list (JSON array)

    def __repr__(self) -> str:
        return (
            f"CartInfo(total_amount={self.total_amount}, "
            f"item_count={self.item_count})"
        )


# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------


@dataclass
class Checkout:
    """
    Checkout domain model.

    Records a checkout request initiated by an Agent, containing merchant
    info, cart, amounts, etc.
    Associations:
      Mandate -> Checkout (many-to-one)
      PaymentToken -> Checkout (one-to-one)
    """

    checkout_id: Optional[str] = None  # Checkout ID
    mandate_id: Optional[str] = None  # Associated Mandate ID
    merchant: Optional[Merchant] = None  # Merchant information
    cart_info: Optional[CartInfo] = None  # Cart information
    checkout_hash: Optional[str] = None  # Checkout hash (tamper-proof)
    ext_info: Optional[str] = None  # Extension information (JSON)
    reference_checkout_id: Optional[str] = None  # Associated TR checkout ID
    gmt_create: Optional[datetime] = None  # Creation time
    gmt_modified: Optional[datetime] = None  # Modification time

    # ------------------------------------------------------------------
    # Extension info operations
    # ------------------------------------------------------------------

    def fetch_ext_info(self, key: CheckoutExtendType) -> Optional[str]:
        """
        Get extension info value.

        :param key: extension info key
        :return: extension info value, or None if not found
        """
        if not self.ext_info:
            return None
        try:
            data = json.loads(self.ext_info)
            return data.get(key.value)
        except (json.JSONDecodeError, TypeError):
            return None

    def put_ext_info(self, key: CheckoutExtendType, value: str) -> None:
        """
        Add extension info.

        :param key: extension info key
        :param value: extension info value (skipped if None)
        """
        if value is None:
            return
        if not self.ext_info:
            data: dict = {}
        else:
            try:
                data = json.loads(self.ext_info)
            except (json.JSONDecodeError, TypeError):
                data = {}
        data[key.value] = value
        self.ext_info = json.dumps(data, ensure_ascii=False)

    def __repr__(self) -> str:
        return (
            f"Checkout(checkout_id={self.checkout_id!r}, "
            f"mandate_id={self.mandate_id!r}, "
            f"merchant={self.merchant}, cart_info={self.cart_info}, "
            f"gmt_create={self.gmt_create}, gmt_modified={self.gmt_modified})"
        )

