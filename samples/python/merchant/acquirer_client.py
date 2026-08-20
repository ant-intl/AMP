"""Acquirer HTTP client — calls the Acquirer service at POST /acquirer/pay.

Two implementations:
  - MockAcquirerClient: always succeeds (for unit tests)
  - HttpAcquirerClient: real HTTP client using common.http_client.http_post
"""
from __future__ import annotations

import logging
import pathlib
import sys
import uuid

_project_root = pathlib.Path(__file__).resolve().parents[3]
_src_python = str(_project_root / "src" / "python")
if _src_python not in sys.path:
    sys.path.insert(0, _src_python)

from common.http_client import http_post
from common.multi_currency_money import MultiCurrencyMoney

from .models import AcquirerPaymentResponse

logger = logging.getLogger("merchant.acquirer_client")


# ---------------------------------------------------------------------------
# MockAcquirerClient — Simulated acquirer, always returns success
# ---------------------------------------------------------------------------


class MockAcquirerClient:
    """Mock acquirer client (always succeeds)."""

    def submit_payment(
        self, *, checkout_id: str, amount: MultiCurrencyMoney, payment_token: str, merchant_id: str
    ) -> AcquirerPaymentResponse:
        """Simulate acquirer request, generate ACQ-{uuid8} transaction ID."""
        acquirer_payment_id = f"ACQ-{uuid.uuid4().hex[:8].upper()}"
        return AcquirerPaymentResponse(
            success=True,
            acquirer_payment_id=acquirer_payment_id,
            message="Payment approved by mock acquirer",
        )


# ---------------------------------------------------------------------------
# HttpAcquirerClient — Real HTTP client calling the Acquirer service
# ---------------------------------------------------------------------------


class HttpAcquirerClient:
    """Real HTTP client calling the Acquirer service.

    Uses common.http_client.http_post (httpx-based) with automatic
    request/response logging in the unified structured format.
    Acquirer endpoint: POST /acquirer/pay
    """

    def __init__(self, base_url: str = "http://localhost:8085"):
        self._base_url = base_url.rstrip("/")

    def submit_payment(
        self, *, checkout_id: str, amount: MultiCurrencyMoney, payment_token: str, merchant_id: str
    ) -> AcquirerPaymentResponse:
        """Submit payment to Acquirer via HTTP POST."""
        url = f"{self._base_url}/acquirer/pay"
        payload = {
            "checkoutId": checkout_id,
            "amount": {"cent": amount.fetch_minor_units(), "currency": amount.currency_code},
            "paymentToken": payment_token,
            "merchantId": merchant_id,
        }

        try:
            resp = http_post(url, json=payload, logger_name="merchant.acquirer_client")
            result = resp.json()
        except Exception as e:
            logger.error("Acquirer HTTP call failed: %s", e)
            return AcquirerPaymentResponse(
                success=False,
                acquirer_payment_id="",
                message="Acquirer service unavailable",
            )

        # Parse acquirer response — support both simple and full format
        success = result.get("success", False)
        data = result.get("data", {})
        payment_id = (
            data.get("transactionId", "")
            or data.get("paymentId", "")
            or result.get("paymentId", "")
        )
        message = (
            data.get("status", "")
            or result.get("resultMessage", "")
        )

        return AcquirerPaymentResponse(
            success=success,
            acquirer_payment_id=payment_id,
            message=message or ("Payment approved" if success else "Payment declined"),
        )
