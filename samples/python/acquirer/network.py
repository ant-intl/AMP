"""A+ (AlipayPlus) Payment Network — simulates A+ payment processing locally.

Acquirer package's A+ network mock. When the real A+ network (port 8083) is unavailable,
this provides in-process fallback matching the real A+ network interface contract:
  POST /network/pay
    Request (ApsPayBody):  {paymentRequestId, paymentMethod: {paymentMethodId}, paymentAmount: {currency, value}}
    Response: {success: true, data: {payment_id: str, status: "SUCCESS", amount: {currency, value}}}

Validates payment tokens via CGCP prefix rule,
processes settlement, records payments for query/debug.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any

from acquirer.config import CGCP_APLUS_PREFIX

logger = logging.getLogger("acquirer.network")


class AplusNetwork:
    """In-process A+ payment network mock.

    Interface matches the real A+ network's ApsPayBody contract:
      process_payment(aps_pay_body)

    Used as fallback when the real A+ network HTTP service is unavailable.
    """

    def __init__(self) -> None:
        self._payments: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def process_payment(
        self,
        aps_pay_body: dict[str, Any],
    ) -> dict[str, Any]:
        """Mock A+ network: validate token via CGCP prefix + process settlement.

        Matches real A+ network contract (ApsPayBody):
        Args:
            aps_pay_body: {paymentRequestId, paymentMethod: {paymentMethodId}, paymentAmount: {currency, value}}
        """
        payment_request_id = aps_pay_body.get("paymentRequestId", "")
        payment_token = aps_pay_body.get("paymentMethod", {}).get("paymentMethodId", "")
        payment_amount = aps_pay_body.get("paymentAmount", {})

        # CGCP prefix validation
        if not payment_token.startswith(CGCP_APLUS_PREFIX):
            return {
                "success": False,
                "resultCode": "PAYMENT_TOKEN_INVALID",
                "resultMessage": f"mock: token '{payment_token[:8]}...' does not match A+ prefix '{CGCP_APLUS_PREFIX}'",
            }

        # Settlement
        payment_id = f"aplus-mock-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        with self._lock:
            self._payments[payment_id] = {
                "payment_id": payment_id,
                "payment_request_id": payment_request_id,
                "payment_token": payment_token,
                "aps_pay_body": aps_pay_body,
                "status": "SUCCESS",
                "amount": payment_amount,
            }

        logger.info("[A+Mock] payment settled: %s, prId=%s, token=%s",
                     payment_id, payment_request_id, payment_token[:8])

        return {
            "success": True,
            "resultCode": "SUCCESS",
            "resultMessage": "SUCCESS",
            "data": {
                "paymentId": payment_id,
                "status": "SUCCESS",
                "amount": payment_amount,
            },
        }

    def get_payment(self, payment_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._payments.get(payment_id)

    def list_payments(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._payments.values())

    def reset(self) -> None:
        with self._lock:
            self._payments.clear()

    def get_state(self) -> dict[str, Any]:
        return {"payments": self._payments}
