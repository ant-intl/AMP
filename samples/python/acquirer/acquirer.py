"""Acquirer Service — HTTP demo implementing CGCP paymentToken recognition and A+ network routing.

Payment chain flow:
  Merchant → Acquirer (CGCP identifies token prefix → routes to A+ network) → A+ Network → Acquirer → Merchant

CGCP (Credential Gateway Card Processing) token identification rules:
  A+ paymentToken starts with prefix "28166623".
  Acquirer checks the token prefix to identify the payment network and route accordingly.

  Downstream A+ network contract (matches ApsPayBody):
    POST /network/pay  {paymentRequestId, paymentMethod: {paymentMethodId}, paymentAmount: {currency, value}}

  AplusNetwork (network.py) provides a local mock for testing;
  in production the acquirer calls the real A+ network HTTP service.

File structure:
    1. CGCP rules
    2. HTTP endpoints (merchant-facing)
    3. A+ network HTTP client
    4. Payment store & private helpers
"""

from __future__ import annotations

import httpx
import logging
import os
import pathlib
import sys
import threading
from datetime import datetime, timezone
from typing import Any

_project_root = pathlib.Path(__file__).resolve().parents[2]
_src_python = str(_project_root / "src" / "python")
if _src_python not in sys.path:
    sys.path.insert(0, _src_python)

from fastapi import FastAPI
from pydantic import BaseModel, Field

from common.multi_currency_money import MultiCurrencyMoney

from acquirer.config import (
    CGCP_FIXED_PREFIX,
    CGCP_PROTOCOL_VERSION,
    CGCP_INSTITUTION_CODE_ALIPAY_PLUS,
    CGCP_BUSINESS_TYPE_PAYMENT_TOKEN,
    CGCP_APLUS_PREFIX,
    ALIPAYPLUS_NETWORK_BASE_URL,
    ResultCode,
    MERCHANT_REGISTRY,
    DEFAULT_MERCHANT_INFO,
)
from common.utils import gen_id

logger = logging.getLogger("acquirer")


def _parse_cgcp_prefix(payment_token: str) -> dict[str, Any]:
    """CGCP rule: parse paymentToken into IIN + protocol version + institution code + business type for routing.

    Token format: IIN(2) + ProtocolVersion(1) + InstitutionCode(3) + BusinessType(2) = 8 chars header
    
    Returns:
        {
            "iin": str,                    # IIN prefix (e.g. "28")
            "protocol_version": str,       # Protocol version (e.g. "1")
            "institution_code": str,       # Institution code (e.g. "666")
            "business_type": str,          # Business type (e.g. "23")
            "iin_identified_family": str,  # Family name (e.g. "AlipayPlus-family", "unknown")
            "identified_network": str,      # Final routing target (e.g. "AlipayPlus", "unknown")
            "prefix_matched": bool,         # Whether full prefix matched
        }
    """
    if not payment_token:
        return {
            "iin": "",
            "protocol_version": "",
            "institution_code": "",
            "business_type": "",
            "iin_identified_family": "unknown",
            "identified_network": "unknown",
            "prefix_matched": False,
        }

    # Step 1: Parse CGCP header fields
    iin = payment_token[:2]                              # IIN (2 chars)
    protocol_version = payment_token[2:3]                # Protocol version (1 char)
    institution_code = payment_token[3:6]                # Institution code (3 chars)
    business_type = payment_token[6:8]                   # Business type (2 chars)

    # Step 2: Identify family based on Fixed Prefix
    if iin == CGCP_FIXED_PREFIX:
        family = "AlipayPlus-family"
    else:
        family = "unknown"

    # Step 3: Route based on all four CGCP fields
    if (iin == CGCP_FIXED_PREFIX 
        and protocol_version == CGCP_PROTOCOL_VERSION
        and institution_code == CGCP_INSTITUTION_CODE_ALIPAY_PLUS
        and business_type == CGCP_BUSINESS_TYPE_PAYMENT_TOKEN):
        identified_network = "AlipayPlus"
        prefix_matched = True
    else:
        identified_network = "unknown"
        prefix_matched = False

    return {
        "iin": iin,
        "protocol_version": protocol_version,
        "institution_code": institution_code,
        "business_type": business_type,
        "iin_identified_family": family,
        "identified_network": identified_network,
        "prefix_matched": prefix_matched,
    }


def is_aplus_token(payment_token: str) -> bool:
    """CGCP rule: identify A+ paymentToken via hierarchical prefix check.

    Routing logic: IIN "28" + Version "1" + Institution "666" + BusinessType "23" → AlipayPlus (A+).
    """
    return _parse_cgcp_prefix(payment_token)["prefix_matched"]


# ===================================================================
# Pydantic request models (HTTP contract — Merchant → Acquirer)
# ===================================================================

class PayRequest(BaseModel):
    """Merchant -> Acquirer: initiate payment.

    Fields:
        checkoutId    : str                  — Merchant checkout reference for order association
        amount        : MultiCurrencyMoney   — Payment amount
        paymentToken  : str                  — Payment credential issued by upstream authorization chain
        merchantId    : str                  — Merchant identifier (Acquirer looks up merchant details)
    """
    checkoutId: str = Field(..., description="Merchant checkout ID for order association")
    amount: MultiCurrencyMoney = Field(..., description="Payment amount")
    paymentToken: str = Field(..., description="Payment credential issued by upstream auth chain")
    merchantId: str = Field(..., description="Merchant identifier for lookup in Acquirer registry")


# ===================================================================
# 2. HTTP Endpoints (merchant-facing)
# ===================================================================

app = FastAPI(
    title="Acquirer Service — CGCP Token Recognition & A+ Network Routing",
    description="Acquirer demo: receives payment from merchant, identifies paymentToken via CGCP rules, routes to A+ payment network, returns result.",
    version="1.0.0",
)

_aplus_network: "AplusNetworkClient | None" = None
_payment_store: "_PaymentStore | None" = None


@app.post("/acquirer/pay")
def acquirer_pay(body: PayRequest) -> dict[str, Any]:
    """Merchant -> Acquirer: process a payment.

    CGCP flow:
      1. Receive (checkout_id, amount, payment_token) from merchant
      2. CGCP hierarchical routing: parse IIN "28" → A+ family, network token suffix "23" → A+ network
      3. Build paymentRequestId, checkout, paymentToken object for A+ network
      4. Route to A+ payment network
      5. Return network response to merchant
    """
    try:
        # Parameter validation
        if not body.checkoutId:
            return _fail(ResultCode.INVALID_PARAM, "checkout_id must not be empty")
        if body.amount.fetch_minor_units() <= 0:
            return _fail(ResultCode.INVALID_PARAM, f"amount must be > 0, got {body.amount.fetch_minor_units()}")
        if not body.paymentToken:
            return _fail(ResultCode.INVALID_PARAM, "payment_token must not be empty")
        if not body.merchantId:
            return _fail(ResultCode.INVALID_PARAM, "merchant_id must not be empty")

        # Lookup merchant info from Acquirer registry (with fallback)
        merchant_info = MERCHANT_REGISTRY.get(body.merchantId)
        if not merchant_info:
            logger.warning("[Acquirer] merchant_id=%s not found in registry, using default merchant info",
                           body.merchantId)
            merchant_info = DEFAULT_MERCHANT_INFO

        # Idempotency: if this checkout_id already has a successful payment, return it
        existing = _payment_store.find_by_checkout_id(body.checkoutId)
        if existing:
            logger.info("[Acquirer] idempotent hit: checkoutId=%s, existing payment_id=%s",
                        body.checkoutId, existing["payment_id"])
            return _ok({
                "paymentId": existing["payment_id"],
                "paymentRequestId": existing.get("payment_request_id", ""),
                "checkoutId": existing["checkout_id"],
                "amount": {"cent": existing["amount"].fetch_minor_units(), "currency": existing["amount"].currency_code},
                "cgcpRouting": existing.get("cgcp_routing", {}),
                "networkResponse": existing.get("network_result", {}),
                "processedAt": existing.get("stored_at", ""),
                "idempotent": True,
            })

        # CGCP hierarchical token identification
        parsed = _parse_cgcp_prefix(body.paymentToken)
        logger.info("[CGCP] paymentToken=%s, IIN=%s, version=%s, institution=%s, businessType=%s, family=%s, network=%s, matched=%s",
                    body.paymentToken[:8], parsed["iin"], parsed["protocol_version"], 
                    parsed["institution_code"], parsed["business_type"],
                    parsed["iin_identified_family"], parsed["identified_network"], parsed["prefix_matched"])

        if not parsed["prefix_matched"]:
            return _fail(ResultCode.UNKNOWN_NETWORK,
                         f"CGCP: token '{body.paymentToken[:8]}...' FixedPrefix='{parsed['iin']}' version='{parsed['protocol_version']}' "
                         f"institution='{parsed['institution_code']}' businessType='{parsed['business_type']}' "
                         f"does not match A+ routing rule (FixedPrefix='{CGCP_FIXED_PREFIX}' + version='{CGCP_PROTOCOL_VERSION}' "
                         f"+ institution='{CGCP_INSTITUTION_CODE_ALIPAY_PLUS}' + businessType='{CGCP_BUSINESS_TYPE_PAYMENT_TOKEN}')")

        # Build A+ network request (matches new ProcessPaymentBody contract)
        payment_request_id = f"PR-{gen_id()}"

        # Convert amount to string value for A+ network (minor units)
        amount_value = str(body.amount.fetch_minor_units())
        amount_currency = body.amount.currency_code

        # Build order with merchant info from Acquirer registry
        order = {
            "referenceOrderId": body.checkoutId,
            "orderDescription": f"Checkout {body.checkoutId}",
            "orderAmount": {
                "currency": amount_currency,
                "value": amount_value,
            },
            "merchant": {
                "referenceMerchantId": merchant_info["reference_merchant_id"],
                "merchantMCC": merchant_info["merchant_mcc"],
                "merchantName": merchant_info["merchant_name"],
                "merchantDisplayName": merchant_info["merchant_display_name"],
                "merchantAddress": merchant_info["merchant_address"],
            },
        }

        aplus_request = {
            "paymentRequestId": payment_request_id,
            "order": order,
            "paymentAmount": {
                "currency": amount_currency,
                "value": amount_value,
            },
            "paymentMethod": {
                "paymentMethodType": "CONNECT_WALLET",
                "paymentMethodId": body.paymentToken,
                "paymentMethodMetaData": {
                    "tokenRequestor": "OTHER",
                    "tokenServiceProvider": "ALIPAY_PLUS",
                    "tokenUser": "ShoppingAgent",
                },
            },
            "paymentFactor": {
                "isTokenizationPayment": "true",
                "tokenizationPaymentScenario": "AgenticPay",
            },
        }

        # CGCP routing detail preserved for merchant response (not sent to A+)
        cgcp_routing = {
            "paymentToken": body.paymentToken,
            "identifiedNetwork": parsed["identified_network"],
            "cgcpPrefix": CGCP_APLUS_PREFIX,
            "prefixMatched": True,
            "routingDetail": {
                "iin": parsed["iin"],
                "protocolVersion": parsed["protocol_version"],
                "institutionCode": parsed["institution_code"],
                "businessType": parsed["business_type"],
                "iinIdentifiedFamily": parsed["iin_identified_family"],
            },
        }

        # Call A+ network with new contract format
        network_result = _aplus_network.process_payment(aplus_request)

        # Handle downstream failure
        if not network_result.get("success", False):
            logger.warning("[Acquirer] A+ network returned failure: %s",
                           network_result.get("resultMessage", ""))
            return _fail(ResultCode.INTERNAL_ERROR,
                         f"A+ network processing failed: {network_result.get('resultMessage', 'unknown error')}")

        # Store payment record and return to merchant
        payment_id = gen_id()
        _payment_store.store(
            payment_id=payment_id,
            payment_request_id=payment_request_id,
            checkout_id=body.checkoutId,
            amount=body.amount,
            payment_token=body.paymentToken,
            cgcp_identified_network="AlipayPlus",
            cgcp_routing=cgcp_routing,
            checkout=aplus_request,
            network_result=network_result,
        )

        logger.info(
            "[Acquirer] payment processed: id=%s, prId=%s, checkoutId=%s, token=%s, IIN=%s, version=%s, institution=%s, businessType=%s, network=AlipayPlus",
            payment_id, payment_request_id, body.checkoutId, body.paymentToken[:8],
            parsed["iin"], parsed["protocol_version"], parsed["institution_code"], parsed["business_type"])

        return _ok({
            "paymentId": payment_id,
            "paymentRequestId": payment_request_id,
            "checkoutId": body.checkoutId,
            "amount": {"cent": body.amount.fetch_minor_units(), "currency": body.amount.currency_code},
            "cgcpRouting": cgcp_routing,
            "networkResponse": network_result,
            "processedAt": datetime.now(timezone.utc).isoformat(),
        })

    except _AcquirerException as e:
        return _fail(e.code, e.message)
    except Exception as exc:
        logger.exception("[acquirer/pay] unexpected error")
        return _fail(ResultCode.INTERNAL_ERROR, str(exc))


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "acquirer", "cgcpAplusPrefix": CGCP_APLUS_PREFIX}


# ===================================================================
# 3. A+ Network HTTP Client
# ===================================================================


class AplusNetworkClient:
    """A+ network HTTP client — calls the real A+ network service.

    Acquirer -> A+ Network communication:
    ---------------------------------------------------------------
    POST <aplus_base_url>/network/pay
        Request (matches A+ ApsPayBody):
            paymentRequestId : str   — acquirer-side idempotency key
            paymentMethod    : dict  — {paymentMethodType, paymentMethodId (CGCP token)}
            paymentAmount    : dict  — {currency, value}
        Response:
            success          : bool
            data.payment_id  : str   — A+ network payment ID
            data.status      : str   — SUCCESS / FAILED / PENDING
            data.amount      : dict  — {currency, value}
    """

    def __init__(self, base_url: str = ALIPAYPLUS_NETWORK_BASE_URL) -> None:
        self._base_url = base_url.rstrip("/")

    def process_payment(
            self,
            aps_pay_body: dict[str, Any],
    ) -> dict[str, Any]:
        """Call A+ network via HTTP POST. Returns error on failure."""
        payment_token = aps_pay_body.get("paymentMethod", {}).get("paymentMethodId", "")
        payment_request_id = aps_pay_body.get("paymentRequestId", "")
        logger.info("[A+Network] POST %s/network/pay token=%s reqId=%s",
                    self._base_url, payment_token[:8], payment_request_id)
        try:
            resp = httpx.post(
                f"{self._base_url}/network/pay",
                json=aps_pay_body,
                timeout=5.0,
            )
            return resp.json()
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.error("[A+Network] connection failed: %s", exc)
            return _fail(ResultCode.INTERNAL_ERROR, f"A+ network service unavailable: {exc}")
        except Exception as exc:
            logger.error("[A+Network] request failed: %s", exc)
            return _fail(ResultCode.INTERNAL_ERROR, f"A+ network request failed: {exc}")


# ===================================================================
# 4. Payment Store & Private Helpers
# ===================================================================

class _PaymentStore:
    """In-memory payment record store."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def store(self, *, payment_id: str, **kwargs: Any) -> None:
        with self._lock:
            self._store[payment_id] = {
                "payment_id": payment_id,
                "stored_at": datetime.now(timezone.utc).isoformat(),
                **kwargs,
            }

    def find_by_checkout_id(self, checkout_id: str) -> dict[str, Any] | None:
        """Find a successful payment record by checkout_id (for idempotency)."""
        with self._lock:
            for record in self._store.values():
                if record.get("checkout_id") == checkout_id:
                    return record
        return None


class _AcquirerException(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _ok(data: dict[str, Any] | None = None) -> dict[str, Any]:
    resp: dict[str, Any] = {"success": True, "resultCode": "SUCCESS", "resultMessage": "SUCCESS"}
    if data:
        resp["data"] = data
    return resp


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"success": False, "resultCode": code, "resultMessage": message}


# -- Service instances --
_aplus_network = AplusNetworkClient()
_payment_store = _PaymentStore()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("ACQUIRER_PORT", "8085")), log_level="warning")
