"""AlipayPlus Network (Acquirer) HTTP API — FastAPI service.

Network service is the orchestration layer that coordinates Credential Provider,
Mandate service, and MPP. It handles:
  - Session management (enrollment / mandate IDV sessions)
  - Token management (A+ token storage)
  - Verifiable authorization (L1/L2/L3 generation and verification)
  - CGCP payment token issuance
  - MPP and CP client communication
  - Payment processing

File structure:
    1. Constants
    2. Pydantic request models
    3. Public services (HTTP endpoints)
    4. Internal services (NetworkService, clients, repositories)
    5. Stores & client instances
    6. Private helper methods
"""

from __future__ import annotations

import base64
import functools
import hashlib
import json as _json_mod
import logging
import os
import pathlib
import re
import sys
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Optional, TypeVar

# -------------------------------------------------------------------------
# Ensure the project src/python/ (``schemas``, ``mandate_chain``) and
# samples/python/ (``secret``) are on sys.path when running this file directly.
# -------------------------------------------------------------------------
_project_root = pathlib.Path(__file__).resolve().parents[3]
_src_python = str(_project_root / "src" / "python")
_samples_python = str(_project_root / "samples" / "python")
for _p in (_src_python, _samples_python):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI
from pydantic import BaseModel, Field
from jwcrypto import jwk as _jwk_mod

from common.http_client import http_post
from common.utils import gen_id
from common.multi_currency_money import MultiCurrencyMoney
from common.sqlite_store import SqliteStore, SqliteRepo
from secret import get_aplus_private_key, get_aplus_public_jwk, get_aplus_kid
from schemas.mandate import (
    Budget,
    Mandate,
    MandateConstraints,
    MandateExtendType,
    MandateStatus,
    MandateType,
)
from schemas.checkout import CartInfo, Checkout, Merchant
from alipayplus.stores import MandateModel, PaymentOrderStatus, _PaymentOrderStore, _TokenStore
from mandate_chain import (
    create_alipayplus_layer1,
    verify_agent_chain,
    verify_credential_chain,
)

logger = logging.getLogger("network.server")


# =========================================================================
# 1. Constants
# =========================================================================

# Base URLs — configurable via environment variables
_cp_port = os.environ.get("CREDENTIALS_PROVIDER_PORT", "8082")
_mandate_port = os.environ.get("ALIPAYPLUS_MANDATE_PORT", "8084")
_mpp_port = os.environ.get("MPP_PORT", "8899")
MPP_BASE_URL: str = os.environ.get("MPP_BASE_URL", f"http://localhost:{_mpp_port}/mpp")
CP_BASE_URL: str = os.environ.get("CP_BASE_URL", f"http://localhost:{_cp_port}")
MANDATE_BASE_URL: str = os.environ.get("MANDATE_BASE_URL", f"http://localhost:{_mandate_port}")
_VALID_AUTH_CONTEXT_VALUES: tuple[str, ...] = ("ENROLLMENT", "MANDATE")

# SD-JWT standard-claim pinning for chain verification. The network is the
# intended audience of L2/L3 and trusts A+ as the L1 issuer, so we pin these
# values to reject expired tokens / audience-issuer confusion (RFC 7519 exp/aud/iss).
EXPECTED_L1_ISS: str = os.environ.get("ALIPAYPLUS_EXPECTED_ISS", "alipayplus.com")
EXPECTED_L2_AUD: str = os.environ.get("ALIPAYPLUS_EXPECTED_AUD", "alipayplus.com")
EXPECTED_L3_AUD: str = os.environ.get("ALIPAYPLUS_EXPECTED_AUD", "alipayplus.com")

# Wallet-to-MPP routing: wallet_name → MPP base URL
# When a wallet_name is provided in createAuthorization, the request is routed
# to the corresponding MPP instance. Unknown wallet names fall back to MPP_BASE_URL.
_WALLET_MPP_URL_MAP: dict[str, str] = {
    "ALIPAY_HK":  f"http://localhost:{_mpp_port}/mpp"
}

# -------------------------------------------------------------------------
# CGCP (Contactless Gateway Code Protocol) payment token generator
#
# CGCP Header (8 chars):
#   Fixed Prefix   : "28"   (2 chars) — protocol identifier
#   Protocol Version: "1"   (1 char)  — version 1
#   Institution Code: "666" (3 chars) — Alipay+ institution code
#   Business Type   : "23"   (2 chars) — mandate authorization token
#
# Payload (>= 16 chars): unique identifier for the payment token
# -------------------------------------------------------------------------

_CGCP_FIXED_PREFIX = "28"
_CGCP_PROTOCOL_VERSION = "1"
_CGCP_INSTITUTION_CODE_ALIPAY_PLUS = "666"
_CGCP_BUSINESS_TYPE_PAYMENT_TOKEN = "23"

# Payment token validity duration (minutes)
_PAYMENT_TOKEN_EXPIRY_MINUTES = 10


def _generate_cgcp_payment_token() -> str:
    """Generate a CGCP-compliant payment token.

    Format: Header (8 chars) + Payload (>= 16 chars)
    Header: 28 + 1 + 666 + 23
    Payload: UUID-based unique identifier (32 hex chars)
    """
    header = (
            _CGCP_FIXED_PREFIX
            + _CGCP_PROTOCOL_VERSION
            + _CGCP_INSTITUTION_CODE_ALIPAY_PLUS
            + _CGCP_BUSINESS_TYPE_PAYMENT_TOKEN
    )
    payload = uuid.uuid4().hex
    return header + payload


class ResultCode:
    SUCCESS = "0000"
    PARAM_ILLEGAL = "1001"
    MANDATE_NOT_EXIST = "2001"
    MANDATE_STATUS_INVALID = "2002"
    MANDATE_EXPIRED = "2003"
    MANDATE_BALANCE_INSUFFICIENT = "2004"
    MANDATE_USED_AMOUNT_INSUFFICIENT = "2005"
    TOKEN_NOT_MATCH_MANDATE = "2006"
    CHECKOUT_HASH_INCONSISTENT = "2007"
    MERCHANT_NOT_IN_CONSTRAINTS = "2008"
    REPEAT_REQ_INCONSISTENT = "2009"
    PAYMENT_FAILED = "3001"
    PAYMENT_TOKEN_INVALID = "3002"
    PAYMENT_TOKEN_EXPIRED = "3003"
    PAYMENT_TOKEN_ALREADY_USED = "3004"


_CODE_NAME_MAP: dict[str, str] = {
    ResultCode.SUCCESS: "SUCCESS",
    ResultCode.PARAM_ILLEGAL: "PARAM_ILLEGAL",
    ResultCode.MANDATE_NOT_EXIST: "MANDATE_NOT_EXIST",
    ResultCode.MANDATE_STATUS_INVALID: "MANDATE_STATUS_INVALID",
    ResultCode.MANDATE_EXPIRED: "MANDATE_EXPIRED",
    ResultCode.MANDATE_BALANCE_INSUFFICIENT: "MANDATE_BALANCE_INSUFFICIENT",
    ResultCode.MANDATE_USED_AMOUNT_INSUFFICIENT: "MANDATE_USED_AMOUNT_INSUFFICIENT",
    ResultCode.TOKEN_NOT_MATCH_MANDATE: "TOKEN_NOT_MATCH_MANDATE",
    ResultCode.CHECKOUT_HASH_INCONSISTENT: "CHECKOUT_HASH_INCONSISTENT",
    ResultCode.MERCHANT_NOT_IN_CONSTRAINTS: "MERCHANT_NOT_IN_CONSTRAINTS",
    ResultCode.REPEAT_REQ_INCONSISTENT: "REPEAT_REQ_INCONSISTENT",
    ResultCode.PAYMENT_FAILED: "PAYMENT_FAILED",
    ResultCode.PAYMENT_TOKEN_INVALID: "PAYMENT_TOKEN_INVALID",
    ResultCode.PAYMENT_TOKEN_EXPIRED: "PAYMENT_TOKEN_EXPIRED",
    ResultCode.PAYMENT_TOKEN_ALREADY_USED: "PAYMENT_TOKEN_ALREADY_USED",
}


# =========================================================================
# 2. Pydantic request models (HTTP contract)
# =========================================================================

# -- Shared value-object input models --

class MerchantInput(BaseModel):
    """Merchant info input."""
    merchantId: Optional[str] = None
    merchantName: Optional[str] = None
    merchantMcc: Optional[str] = None
    merchantWebSiteUrl: Optional[str] = None
    storeName: Optional[str] = None


class CartInfoInput(BaseModel):
    """Cart info input."""
    totalAmount: Optional[MultiCurrencyMoney] = None
    itemCount: Optional[int] = None
    items: Optional[str] = None


class CheckoutInput(BaseModel):
    """Checkout info input."""
    merchant: Optional[MerchantInput] = None
    cartInfo: Optional[CartInfoInput] = None
    totalAmount: Optional[MultiCurrencyMoney] = None
    goods: Optional[list[dict[str, Any]]] = None


class ConstraintsInput(BaseModel):
    """Constraints input."""
    budgetAmount: Optional[MultiCurrencyMoney] = None
    merchantNameList: list[str] = Field(default_factory=list)
    merchantMccList: list[str] = Field(default_factory=list)


# -- CP-facing HTTP endpoint request bodies --

class CreateIdvSessionBody(BaseModel):
    authContext: str  # "ENROLLMENT" for binding; "MANDATE" for intent
    agentId: str = ""
    credentialProviderId: str = ""
    customerId: str = ""
    tokenId: str = ""
    sub: str = "user-mock-001"
    intentRaw: str = ""
    intentExpireTime: str = ""
    constraints: Optional[ConstraintsInput] = None
    checkout: Optional[CheckoutInput] = None
    walletName: str = ""  # Target wallet/MPP for session creation


class NotifyAuthorizationBody(BaseModel):
    sessionId: str
    idvResult: str
    idvTime: str
    ispPk: Optional[dict] = None
    ispKid: Optional[str] = None
    l2Serialized: Optional[str] = None
    customerId: Optional[str] = None
    pspId: Optional[str] = None
    tokenExpiryTime: Optional[str] = None
    walletAccountInfo: Optional[dict] = None


class ApplyCredentialBody(BaseModel):
    tokenId: str
    mandateId: str
    l1Serialized: str
    l2Serialized: str
    l3Serialized: Optional[str] = None
    checkout: Optional[CheckoutInput] = None


# -- APS Pay request models --

class ApsMoney(BaseModel):
    currency: str = ""
    value: str = "0"


class ApsMerchantAddress(BaseModel):
    region: str = ""
    city: str = ""


class ApsMerchant(BaseModel):
    referenceMerchantId: str = ""
    merchantMCC: str = ""
    merchantName: str = ""
    merchantDisplayName: str = ""
    merchantAddress: Optional[ApsMerchantAddress] = None


class ApsGoods(BaseModel):
    referenceGoodsId: str = ""
    goodsUnitAmount: Optional[ApsMoney] = None
    goodsQuantity: str = "1"
    goodsName: str = ""


class ApsOrder(BaseModel):
    referenceOrderId: str = ""
    orderDescription: str = ""
    orderAmount: Optional[ApsMoney] = None
    merchant: Optional[ApsMerchant] = None
    goods: list[ApsGoods] = Field(default_factory=list)
    env: dict[str, Any] = Field(default_factory=dict)


class ApsPaymentMethodMetaData(BaseModel):
    tokenRequestor: str = ""
    tokenServiceProvider: str = ""
    tokenUser: str = ""


class ApsPaymentMethod(BaseModel):
    paymentMethodType: str = ""
    paymentMethodId: str = ""
    paymentMethodMetaData: Optional[ApsPaymentMethodMetaData] = None


class ApsPaymentFactor(BaseModel):
    isTokenizationPayment: str = "false"
    tokenizationPaymentScenario: str = ""


class ApsPayBody(BaseModel):
    paymentRequestId: str
    pspId: str = ""
    order: Optional[ApsOrder] = None
    paymentAmount: Optional[ApsMoney] = None
    paymentMethod: Optional[ApsPaymentMethod] = None
    paymentFactor: Optional[ApsPaymentFactor] = None


# =========================================================================
# 3. Public services — HTTP endpoints
# =========================================================================

app = FastAPI(
    title="AlipayPlus Network (Acquirer) API",
    description="Orchestration layer: session/token management, L1/L2/L3 verifiable authorization, payment processing.",
    version="2.0.0",
)

from common.middleware import HttpLoggingMiddleware
app.add_middleware(HttpLoggingMiddleware, logger_name="network.http")

# A+ Platform signing key — from centralized secret store


# -- Network error handling decorator --

def handle_network_errors(func):
    """Decorator: catch NetworkServiceException and unexpected errors uniformly."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NetworkServiceException as exc:
            return _fail(exc.result_code, exc.result_message)
        except Exception as exc:
            logger.exception("[%s] unexpected error", func.__name__)
            return _fail(ResultCode.PARAM_ILLEGAL, str(exc))
    return wrapper


# -- Credential-Provider-facing endpoints --

@app.post("/network/createAuthorization")
@handle_network_errors
def network_create_authorization(body: CreateIdvSessionBody) -> dict:
    """Create an authorization session via MPP.

    Called by CP to start enrollment or mandate intent verification.
    """
    # Step 1: Validate input and derive auth_context
    auth_context_list, auth_context = _validate_create_authorization_body(body)

    # Step 2: Create session
    session_id = gen_id()
    _session_store.put(session_id, {
        "session_id": session_id,
        "auth_context": auth_context,
        "status": "CREATED",
        "auth_context_list": auth_context_list,
        "agent_id": body.agentId,
        "credential_provider_id": body.credentialProviderId,
        "customer_id": body.customerId,
        "token_id": body.tokenId,
        "sub": body.sub,
        "intent_raw": body.intentRaw,
        "intent_expire_time": body.intentExpireTime,
        "constraints": body.constraints.model_dump(exclude_none=True) if body.constraints else None,
        "checkout": body.checkout.model_dump(exclude_none=True) if body.checkout else None,
        "wallet_name": body.walletName,
    })

    # Step 3: Resolve customer ID
    customer_id = _resolve_customer_id_for_mandate(body, auth_context)

    # Step 4: Call MPP and return
    return _call_mpp_create_authorization(body, session_id, customer_id, auth_context_list, body.checkout, body.constraints)


@app.post("/network/notifyAuthorization")
@handle_network_errors
def network_notify_authorization(body: NotifyAuthorizationBody) -> dict:
    """Handle authorization result notification from MPP.

    ENROLLMENT: generate L1, store token, notify CP.
    MANDATE: verify L2, create mandate (via mandate.py), notify CP.
    """
    # Step 1: Validate session exists
    session = _not_none(
        _session_store.get(body.sessionId),
        ResultCode.PARAM_ILLEGAL,
        f"session not found, sessionId={body.sessionId}",
    )

    # Step 2: Route by auth_context
    if session["auth_context"] == "ENROLLMENT":
        return _handle_enrollment_notify(body, session)
    else:
        return _handle_mandate_notify(body, session)


@app.post("/network/applyCredential")
@handle_network_errors
def network_apply_credential(body: ApplyCredentialBody) -> dict:
    """Apply for a payment credential.

    Steps:
        1. Verify SD-JWT credential chain (L1/L2 consistency + chain verification)
        2. Call mandate.py validate (status, expiry, checkout hash, constraints)
        3. Call mandate.py to deduct balance
        4. Advance mandate status
        5. Issue CGCP payment token
    """
    # Step 1: Verify SD-JWT credential chain (L1/L2 match stored records + chain verification)
    _verify_credential_chain(body)

    # Step 1.5: Look up mandate to determine type and get stored checkout
    mandate_record = _tokens.get_by_mandate_id(body.mandateId)
    if not mandate_record:
        return _fail(ResultCode.PARAM_ILLEGAL, f"mandate not found: {body.mandateId}")
    m_type = mandate_record.get("mandate_type", "")

    # Step 2: Call mandate.py to validate intent (status, expiry, checkout hash, constraints)
    # Prefer request checkout; if not provided and IMMEDIATE mode, fall back to stored checkout from L2
    if body.checkout:
        checkout_dict = body.checkout.model_dump(exclude_none=True)
    elif m_type == "IMMEDIATE":
        checkout_dict = mandate_record.get("checkout")  # snake_case from L2 disclosure
    else:
        checkout_dict = None

    validate_result = _call_mandate("/mandate/validate", {
        "mandateId": body.mandateId,
        "mandateType": m_type,
        "checkout": checkout_dict,
    })
    if not validate_result.get("success"):
        return validate_result
    mandate_data = validate_result.get("data", {})
    m_type = mandate_data.get("mandateType", "")

    # Step 3: Call mandate.py to deduct amount
    amount_money = _extract_amount_from_checkout(checkout_dict)

    deduct_result = _call_mandate("/mandate/deduct-amount", {
        "mandateId": body.mandateId,
        "bizSerialNo": gen_id(),
        "cartAmount": {
            "cent": amount_money.fetch_minor_units(),
            "currency": amount_money.currency_code,
        },
    })
    if not deduct_result.get("success"):
        return deduct_result
    deducted_mandate = deduct_result.get("data", {}).get("mandate", {})

    # Step 4: Advance mandate status
    advance_result = _call_mandate("/mandate/advance-status", {"mandateId": body.mandateId})
    mandate_status = advance_result.get("data", {}).get("mandateStatus", deducted_mandate.get("mandateStatus", "ACTIVE"))

    # Step 5: Issue CGCP payment token with 10-minute expiry
    payment_token = _generate_cgcp_payment_token()
    payment_token_expiry = datetime.now(timezone.utc) + timedelta(minutes=_PAYMENT_TOKEN_EXPIRY_MINUTES)
    _tokens.store_payment_token(
        payment_token,
        mandate_id=body.mandateId,
        token_id=body.tokenId,
        checkout=checkout_dict,
        payment_status="ISSUED",
        expiry_time=payment_token_expiry,
        l3_serialized=body.l3Serialized,
    )

    return _ok({
        "paymentToken": payment_token,
        "mandateType": m_type,
        "mandateStatus": mandate_status,
        "deductedAmount": {
            "cent": amount_money.fetch_minor_units(),
            "currency": amount_money.currency_code,
        },
        "budget": deducted_mandate.get("budget"),
    })


# -- Payment processing endpoint --

@app.post("/network/pay")
@handle_network_errors
def network_process_payment(body: ApsPayBody) -> dict:
    """Process a payment using the payment token issued by ATS service."""
    _not_blank(body.paymentRequestId, ResultCode.PARAM_ILLEGAL, "paymentRequestId cannot be blank")
    payment_token = body.paymentMethod.paymentMethodId if body.paymentMethod else ""
    _not_blank(payment_token, ResultCode.PARAM_ILLEGAL, "paymentMethodId cannot be blank")

    result = _payment_svc.process_payment(body)
    return result





# =========================================================================
# 4. Internal services
# =========================================================================

# -------------------------------------------------------------------------
# NetworkService — Payment processing
# -------------------------------------------------------------------------

class NetworkService:
    """Payment Network / Acquirer service.

    Responsibilities:
        - Receive payment requests from merchants
        - Validate payment tokens
        - Process settlement and persist payment orders
        - Return result
    """

    def process_payment(self, body: ApsPayBody) -> dict[str, Any]:
        """Process a payment using the payment token."""
        payment_request_id = body.paymentRequestId
        payment_token = body.paymentMethod.paymentMethodId if body.paymentMethod else ""

        # Idempotency: check if a payment order already exists for this acquirerOrderId
        existing = _payment_orders.get_by_acquirer_order_id(payment_request_id)
        if existing is not None:
            logger.info("[NetworkService] idempotent hit, acquirerOrderId=%s, paymentId=%s", payment_request_id, existing.get("payment_id"))
            return _ok({
                "paymentId": existing.get("payment_id", ""),
                "status": existing.get("status", ""),
                "amount": {"cent": existing.get("amount", 0), "currency": existing.get("currency", "")},
            })

        # Validate payment token
        _validate_payment_token(payment_token)

        # Flip status to USED (consume the token)
        _tokens.update_payment_token(payment_token, payment_status="USED")

        # Call MPP /pay to deTokenize payment token and settle
        return self._settle_via_mpp(body)

    def _settle_via_mpp(self, body: ApsPayBody) -> dict[str, Any]:
        """Call MPP /pay, persist the payment order, and return the result."""
        payment_request_id = body.paymentRequestId
        payment_token = body.paymentMethod.paymentMethodId if body.paymentMethod else ""

        # Extract amount from paymentAmount
        if body.paymentAmount:
            amount_money = MultiCurrencyMoney.of(body.paymentAmount.value, body.paymentAmount.currency)
        else:
            amount_money = MultiCurrencyMoney.of(0, "USD")

        mpp_resp = _mpp_client.pay(
            payment_token=payment_token,
            amount={"cent": amount_money.fetch_minor_units(), "currency": amount_money.currency_code},
        )

        payment_id = f"pay-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{gen_id()[:8]}"
        mpp_result = mpp_resp.get("result", {})
        pay_success = mpp_result.get("resultStatus") == "S"

        if not pay_success:
            _payment_orders.save(
                payment_id=payment_id,
                acquirer_order_id=payment_request_id,
                amount=amount_money.fetch_minor_units(),
                currency=amount_money.currency_code,
                status=PaymentOrderStatus.FAIL,
            )
            return _fail(
                mpp_result.get("resultCode", "PAYMENT_FAILED"),
                mpp_result.get("resultMessage", "MPP pay failed"),
            )

        _payment_orders.save(
            payment_id=payment_id,
            acquirer_order_id=payment_request_id,
            amount=amount_money.fetch_minor_units(),
            currency=amount_money.currency_code,
            status=PaymentOrderStatus.SUCCESS,
        )
        logger.info("[NetworkService] payment processed: %s, token=%s", payment_id, payment_token)
        return _ok({
            "paymentId": payment_id,
            "status": "SUCCESS",
            "amount": {"cent": amount_money.fetch_minor_units(), "currency": amount_money.currency_code},
        })

    def get_payments(self) -> list[dict[str, Any]]:
        return _payment_orders.list_all()

    def get_payment(self, payment_id: str) -> dict[str, Any] | None:
        return _payment_orders.get(payment_id)

    def reset(self) -> None:
        _payment_orders.clear()


# -------------------------------------------------------------------------
# External service clients
# -------------------------------------------------------------------------

class _MppClient:
    """HTTP client for MPP (wallet/identity-verification provider).

    Adapts to the real MPP service API contract (camelCase fields).
    """

    def create_authorization(self, *, auth_session_id: str, customer_id: str,
                             agent_id: str,
                             auth_context: list[str],
                             wallet_name: str = "",
                             l1_serialized: str = "",
                             intent: dict[str, Any] | None = None,
                             checkout: dict[str, Any] | None = None,
                             ) -> dict[str, Any]:
        """Call MPP POST /createAuthorization.

        Request body follows MPP's CreateAuthorizationBody contract (camelCase).
        """
        mpp_url = _resolve_mpp_base_url(wallet_name)
        payload: dict[str, Any] = {
            "authSessionId": auth_session_id,
            "agentId": agent_id,
            "customerId": customer_id,
            "authContext": auth_context,
        }
        if l1_serialized:
            payload["l1Serialized"] = l1_serialized
        if intent:
            payload["intent"] = intent
        if checkout:
            payload["checkout"] = checkout
        logger.debug("[MPP] POST %s/createAuthorization session=%s, wallet=%s, ctx=%s",
                    mpp_url, auth_session_id, wallet_name or "default", auth_context)
        resp = http_post(f"{mpp_url}/createAuthorization", json=payload,
                         logger_name="network.http-client")
        return resp.json()

    def pay(self, *, payment_token: str, amount: dict[str, Any] | None = None,
            wallet_name: str = "") -> dict[str, Any]:
        """Call MPP /pay to deTokenize payment token and settle."""
        mpp_url = _resolve_mpp_base_url(wallet_name)
        logger.debug("[MPP] POST %s/pay token=%s...", mpp_url, payment_token[:16])
        resp = http_post(f"{mpp_url}/pay", json={
            "paymentToken": payment_token,
            "amount": amount,
        }, logger_name="network.http-client")
        return resp.json()


class _CpClient:
    """HTTP client for Credential Provider notifications.

    Uses TestClient for in-process calls when CP app is available locally.
    """

    def _call_cp(self, path: str, json: dict) -> dict[str, Any]:
        """Call CP endpoint — prefer in-process TestClient, fallback to HTTP."""
        try:
            from fastapi.testclient import TestClient
            # Try to find the CP app in the running process
            import alipayplus.network as _net_mod
            cp_app = getattr(_net_mod, '_cp_app_ref', None)
            if cp_app is not None:
                resp = TestClient(cp_app).post(path, json=json)
                return resp.json()
        except Exception:
            pass
        # Fallback: real HTTP call
        resp = http_post(f"{CP_BASE_URL}{path}", json=json, logger_name="network.http-client")
        return resp.json()

    def notify_binding_result(self, *, session_id: str,
                              token_id: str, l1_serialized: str,
                              wallet_account_info: Optional[dict] = None) -> dict[str, Any]:
        """Notify CP that binding (ENROLLMENT) is complete via unified notifyAuthorization."""
        logger.debug("[CP] POST %s/credential-provider/notifyAuthorization session=%s, token=%s",
                    CP_BASE_URL, session_id, token_id)
        payload: dict[str, Any] = {
            "sessionId": session_id,
            "authContext": "ENROLLMENT",
            "tokenId": token_id,
            "l1Serialized": l1_serialized,
        }
        if wallet_account_info:
            payload["walletAccountInfo"] = wallet_account_info
        return self._call_cp("/credential-provider/notifyAuthorization", payload)

    def notify_intent_result(self, *, session_id: str,
                             mandate_id: str, l2_serialized: str) -> dict[str, Any]:
        """Notify CP that intent (MANDATE) IDV is complete via unified notifyAuthorization."""
        logger.debug("[CP] POST %s/credential-provider/notifyAuthorization session=%s, mandate=%s",
                    CP_BASE_URL, session_id, mandate_id)
        return self._call_cp("/credential-provider/notifyAuthorization", {
            "sessionId": session_id,
            "authContext": "MANDATE",
            "mandateId": mandate_id,
            "l2Serialized": l2_serialized,
        })


# =========================================================================
# 5. Stores & client instances
# =========================================================================

_session_store = SqliteStore()
_tokens = _TokenStore()
_payment_orders = _PaymentOrderStore()
_mpp_client = _MppClient()
_cp_client = _CpClient()
_payment_svc = NetworkService()


def _session_store_update(session_id: str, **kwargs: Any) -> None:
    """Read-modify-write a session dict in _session_store atomically."""
    _session_store.acquire()
    try:
        session = _session_store.get_locked(session_id)
        if session is not None:
            session.update(kwargs)
            _session_store.update_locked(session_id, session)
    finally:
        _session_store.release()


# =========================================================================
# 6. Private helper methods
# =========================================================================

# -- Exception & assertion helpers --

class NetworkServiceException(Exception):
    """Raised when a network business rule is violated."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.result_code = code
        self.result_message = message


_T = TypeVar("_T")


def _is_true(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise NetworkServiceException(code, message)


def _not_none(value: _T | None, code: str, message: str) -> _T:
    if value is None:
        raise NetworkServiceException(code, message)
    return value


def _not_blank(value: str | None, code: str, message: str) -> None:
    if not value or not value.strip():
        raise NetworkServiceException(code, message)


def _ok(data: dict[str, Any] | None = None) -> dict[str, Any]:
    resp: dict[str, Any] = {"success": True, "resultCode": "SUCCESS", "resultMessage": "SUCCESS"}
    if data:
        resp["data"] = data
    return resp


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"success": False, "resultCode": _CODE_NAME_MAP.get(code, code), "resultMessage": message}



def _validate_payment_token(payment_token: str) -> None:
    _not_blank(payment_token, ResultCode.PARAM_ILLEGAL, "payment token cannot be blank")
    # Validate payment token record from store: existence, status, expiry
    pt_record = _tokens.get_payment_token(payment_token)
    _not_none(
        pt_record,
        ResultCode.PAYMENT_TOKEN_INVALID,
        f"payment token not found, paymentToken={payment_token}",
    )
    assert pt_record is not None  # for type checker

    # Check status: must be ISSUED
    payment_status = pt_record.get("payment_status", "")
    _is_true(
        payment_status == "ISSUED",
        ResultCode.PAYMENT_TOKEN_ALREADY_USED if payment_status == "USED" else ResultCode.PAYMENT_TOKEN_INVALID,
        f"payment token is not valid, status={payment_status}",
    )

    # Check expiry
    expiry_time_str = pt_record.get("expiry_time")
    if expiry_time_str:
        try:
            expiry_time = datetime.fromisoformat(expiry_time_str.replace("Z", "+00:00"))
            _is_true(
                datetime.now(timezone.utc) <= expiry_time,
                ResultCode.PAYMENT_TOKEN_EXPIRED,
                f"payment token expired, expiryTime={expiry_time_str}",
            )
        except ValueError:
            pass  # If can't parse, skip expiry check


# -- Amount extraction helper --

def _extract_amount_from_checkout(checkout_dict: dict[str, Any] | None) -> MultiCurrencyMoney:
    """Extract amount from a checkout dict as MultiCurrencyMoney.

    Handles both snake_case (stored L2 disclosure) and camelCase (request) formats.
    Returns zero USD when checkout_dict is None.
    """
    if not checkout_dict:
        return MultiCurrencyMoney.of(0, "USD")
    if "total_amount" in checkout_dict:
        # snake_case (from stored L2 disclosure)
        ta = checkout_dict.get("total_amount", {})
        amount_cent = ta.get("amount", 0)
        amount_currency = ta.get("currency", "USD")
    else:
        # camelCase (from request)
        ta = checkout_dict.get("totalAmount", {})
        amount_cent = ta.get("cent", 0)
        amount_currency = ta.get("currency", "USD")
    return MultiCurrencyMoney.of(amount_cent, amount_currency)


# -- Mandate service client (calls mandate.py via TestClient in-process) --

def _call_mandate(path: str, body: dict[str, Any]) -> dict[str, Any]:
    """Call the Mandate service via TestClient (in-process)."""
    from fastapi.testclient import TestClient
    from alipayplus.mandate import app as mandate_app
    client = TestClient(mandate_app)
    response = client.post(path, json=body)
    return response.json()


def _resolve_mpp_base_url(wallet_name: str) -> str:
    """Resolve MPP base URL by wallet_name.

    Looks up _WALLET_MPP_URL_MAP for a matching wallet; falls back to MPP_BASE_URL.
    """
    if wallet_name:
        return _WALLET_MPP_URL_MAP.get(wallet_name.upper(), MPP_BASE_URL)
    return MPP_BASE_URL


# -- Challenge computation --

def _sha256_hex(value: str) -> str:
    """Compute SHA-256 hex digest (lowercase, 64 chars)."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    """Canonical JSON: sorted keys, compact separators, normalized values."""
    return _json_mod.dumps(_normalize_for_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _normalize_for_canonical(v: Any) -> Any:
    """Recursively normalize: strip strings, sort dicts, recurse into nested structures."""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, dict):
        return {k: _normalize_for_canonical(val) for k, val in sorted(v.items())}
    if isinstance(v, list):
        return [_normalize_for_canonical(item) for item in v]
    return v


def _normalize_value(value: Any) -> Any:
    """Recursively convert camelCase dict keys to snake_case for canonical comparison."""
    def _to_snake(key: str) -> str:
        s = re.sub(r"([A-Z]+)", r"_\1", key).lower()
        return s.lstrip("_")
    if isinstance(value, dict):
        return {_to_snake(k): _normalize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_value(i) for i in value]
    return value


def _sha256_b64url(s: str) -> str:
    """SHA-256 then Base64URL encode without padding."""
    digest = hashlib.sha256(s.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _compute_checkout_hash(data: Any) -> str:
    """Compute checkout hash: B64U(SHA-256(canonical(normalized JSON)))."""
    normalized = _normalize_value(data)
    canonical = _canonical_json(normalized)
    return _sha256_b64url(canonical)


# -- Format converters --

def _to_chain_checkout(checkout: CheckoutInput | None) -> dict[str, Any] | None:
    """Convert CheckoutInput to mandate_chain snake_case format."""
    if not checkout:
        return None
    ta = checkout.totalAmount
    merchant = checkout.merchant
    result: dict[str, Any] = {
        "total_amount": {"currency": ta.currency_code if ta else "USD", "amount": ta.fetch_minor_units() if ta else 0},
        "merchant": {
            "reference_merchant_id": merchant.merchantId or "" if merchant else "",
            "merchant_name": merchant.merchantName or "" if merchant else "",
            "merchant_mcc": merchant.merchantMcc or "" if merchant else "",
        },
    }
    if checkout.goods:
        result["goods"] = checkout.goods
    return result


def _to_chain_constraints(constraints: ConstraintsInput | None) -> dict[str, Any] | None:
    """Convert ConstraintsInput to mandate_chain snake_case format."""
    if not constraints:
        return None
    ba = constraints.budgetAmount
    return {
        "budget_amount": {"currency": ba.currency_code if ba else "USD", "amount": ba.fetch_minor_units() if ba else 0},
        "merchant_name_list": constraints.merchantNameList,
        "merchant_mcc_list": constraints.merchantMccList,
    }


# -- Endpoint flow helpers --

def _validate_create_authorization_body(body: CreateIdvSessionBody) -> tuple[list[str], str]:
    """Validate auth_context, agentId, credentialProviderId. Return (auth_context_list, auth_context)."""
    auth_context_str = body.authContext.upper().strip()
    auth_context_list = [ctx.strip() for ctx in auth_context_str.split(",") if ctx.strip()]
    _is_true(len(auth_context_list) > 0, ResultCode.PARAM_ILLEGAL, "authContext cannot be empty")
    _is_true(
        all(ctx in _VALID_AUTH_CONTEXT_VALUES for ctx in auth_context_list),
        ResultCode.PARAM_ILLEGAL,
        f"authContext values must be one of {_VALID_AUTH_CONTEXT_VALUES}",
    )
    auth_context = "MANDATE" if "MANDATE" in auth_context_list else "ENROLLMENT"
    _not_blank(body.agentId, ResultCode.PARAM_ILLEGAL, "agentId is required")
    _not_blank(body.credentialProviderId, ResultCode.PARAM_ILLEGAL, "credentialProviderId is required")
    # An AUTONOMOUS mandate (constraints instead of a single checkout) must carry
    # the expiry the user stated: the wallet derives the L2 lifetime from it and
    # nothing along the chain defaults it.
    if auth_context == "MANDATE" and body.constraints is not None:
        _not_blank(body.intentExpireTime, ResultCode.PARAM_ILLEGAL,
                   "intentExpireTime is required for an AUTONOMOUS mandate")
    return auth_context_list, auth_context


def _resolve_customer_id_for_mandate(body: CreateIdvSessionBody, auth_context: str) -> str:
    """For MANDATE sessions, look up customer_id from the stored token record."""
    customer_id = body.customerId
    if auth_context == "MANDATE":
        token_id = body.tokenId
        if token_id:
            token_record = _tokens.get_by_token_id(token_id)
            if token_record:
                stored_customer_id = token_record.get("customer_id", "")
                if stored_customer_id:
                    customer_id = stored_customer_id
    return customer_id


def _build_mpp_checkout(checkout: CheckoutInput) -> dict[str, Any]:
    """Convert CheckoutInput to MPP's CheckoutIn camelCase contract."""
    checkout_data = checkout.model_dump(exclude_none=True)
    # CheckoutInput fields are already camelCase
    return checkout_data


def _call_mpp_create_authorization(
    body: CreateIdvSessionBody, session_id: str, customer_id: str,
    auth_context_list: list[str],
    checkout: CheckoutInput | None = None,
    constraints: ConstraintsInput | None = None,
) -> dict:
    """Call MPP /createAuthorization and build the response."""
    # Build camelCase checkout for MPP's CheckoutIn contract
    mpp_checkout = _build_mpp_checkout(checkout) if checkout else None

    # Build intent for MPP — include constraints so MPP can determine AUTONOMOUS vs IMMEDIATE
    mpp_intent: dict[str, Any] | None = None
    if body.intentRaw:
        mpp_intent = {
            "raw": body.intentRaw,
            "desc": "",
            "expireTime": body.intentExpireTime,
        }
        if constraints:
            mpp_intent["constraints"] = constraints.model_dump(exclude_none=True)

    # For MANDATE: look up L1 from token store so MPP can embed it in L2 sd_hash
    l1_for_mpp = ""
    if "MANDATE" in auth_context_list and body.tokenId:
        token_record = _tokens.get_by_token_id(body.tokenId)
        if token_record:
            l1_for_mpp = token_record.get("l1_serialized", "")

    mpp_result = _mpp_client.create_authorization(
        auth_session_id=session_id,
        customer_id=customer_id,
        agent_id=body.agentId,
        auth_context=auth_context_list,
        wallet_name=body.walletName,
        l1_serialized=l1_for_mpp,
        intent=mpp_intent,
        checkout=mpp_checkout,
    )
    # MPP returns camelCase: authId, passkeyAuthInfo
    auth_id = mpp_result.get("authId", "")
    passkey_info = mpp_result.get("passkeyAuthInfo", {})
    _session_store_update(session_id, auth_id=auth_id)
    return _ok({
        "sessionId": session_id,
        "authId": auth_id,
        "passkeyOptions": passkey_info,
        "status": "IDV_SESSION_CREATED",
    })


# -- notifyAuthorization helpers --

def _handle_enrollment_notify(body: NotifyAuthorizationBody, session: dict[str, Any]) -> dict:
    """ENROLLMENT flow: generate L1, store token, notify CP."""
    isp_pk = _not_none(body.ispPk, ResultCode.PARAM_ILLEGAL, "ispPk is required for ENROLLMENT session")
    isp_jwk = _jwk_mod.JWK(**isp_pk)
    l1_serialized = create_alipayplus_layer1(
        sub=session.get("sub"),
        isp_public_key=isp_jwk,
        isp_type=session.get("isp_type", "MPP"),
        isp_name=session.get("isp_name", "ALIPAY_HK"),
        private_key=get_aplus_private_key(),
        kid=get_aplus_kid(),
    )
    token_id = gen_id()
    _tokens.store_token(
        token_id,
        l1_serialized=l1_serialized,
        session_id=body.sessionId,
        isp_pk=body.ispPk,
        customer_id=body.customerId or "",
        psp_id=body.pspId or session.get("isp_name", ""),
        expiry_time=body.tokenExpiryTime or "",
    )
    _session_store_update(body.sessionId, status="COMPLETED", token_id=token_id, l1_serialized=l1_serialized)
    _cp_client.notify_binding_result(
        session_id=body.sessionId, token_id=token_id, l1_serialized=l1_serialized,
        wallet_account_info=body.walletAccountInfo,
    )
    return _ok({"tokenId": token_id, "l1Serialized": l1_serialized})


def _handle_mandate_notify(body: NotifyAuthorizationBody, session: dict[str, Any]) -> dict:
    """MANDATE flow: verify L2, parse disclosures, create mandate (via mandate.py), notify CP."""
    # Step 1: Verify L2 and extract disclosures
    l2_serialized = _not_none(body.l2Serialized, ResultCode.PARAM_ILLEGAL, "l2Serialized is required for MANDATE session")
    disc_map = _verify_l2_and_extract_disclosures(l2_serialized, session)

    # Step 2: Determine mandate type
    mandate_type = _determine_mandate_type_from_disclosures(disc_map)

    # Step 3: Generate mandate ID
    mandate_id = gen_id()

    # Step 4: Build create mandate input from disclosures
    create_input = _build_create_mandate_input(disc_map, session, body.sessionId, mandate_id, mandate_type)

    # Step 5: Create mandate via mandate.py
    create_result = _call_mandate("/mandate/create", create_input)
    if not create_result.get("success"):
        return create_result

    # Step 6: Store mandate metadata
    checkout_for_storage = _extract_checkout_for_storage(disc_map, mandate_type)
    _tokens.store_mandate(
        mandate_id,
        token_id=session.get("token_id", ""),
        mandate_type=mandate_type,
        l2_serialized=l2_serialized,
        session_id=body.sessionId,
        checkout=checkout_for_storage,
    )
    _session_store_update(body.sessionId, status="COMPLETED", mandate_id=mandate_id)

    # Step 7: Notify CP
    _cp_client.notify_intent_result(
        session_id=body.sessionId, mandate_id=mandate_id, l2_serialized=l2_serialized,
    )
    return _ok({"mandateId": mandate_id, "mandateType": mandate_type, "l2Serialized": l2_serialized})


def _verify_l2_and_extract_disclosures(l2_serialized: str, session: dict[str, Any]) -> dict[str, Any]:
    """Verify L2 against stored L1, then decode SD-JWT disclosures into a dict."""
    # Verify L2 against stored L1
    token_id = session.get("token_id", "")
    _is_true(bool(token_id), ResultCode.PARAM_ILLEGAL, "token_id not found in session — enrollment must complete first")
    token_record = _not_none(
        _tokens.get_by_token_id(token_id),
        ResultCode.PARAM_ILLEGAL,
        f"token not found, tokenId={token_id}",
    )
    l1_serialized = token_record.get("l1_serialized", "")
    _is_true(bool(l1_serialized), ResultCode.PARAM_ILLEGAL, "L1 not found in token record")
    l2_verify_result = verify_credential_chain(
        l1_serialized=l1_serialized,
        l2_serialized=l2_serialized,
        alipayplus_public_key=_jwk_mod.JWK(**get_aplus_public_jwk()),
        expected_iss=EXPECTED_L1_ISS,
        expected_l2_aud=EXPECTED_L2_AUD,
    )
    _is_true(
        l2_verify_result.get("valid", False),
        ResultCode.PARAM_ILLEGAL,
        f"L2 verification failed: {', '.join(l2_verify_result.get('errors', [])) or l2_verify_result.get('error', 'unknown')}",
    )
    logger.info("[network/notifyAuthorization] L2 verification passed for session=%s", session.get("session_id"))

    # Decode SD-JWT disclosures
    parts = l2_serialized.split("~")
    disclosures: list[Any] = []
    for disc_str in parts[1:]:
        if disc_str:
            try:
                padded = disc_str + "=" * (-len(disc_str) % 4)
                decoded = base64.urlsafe_b64decode(padded)
                disclosures.append(_json_mod.loads(decoded))
            except Exception:
                pass
    disc_map: dict[str, Any] = {}
    for d in disclosures:
        if isinstance(d, list) and len(d) == 3:
            disc_map[str(d[1])] = d[2]
    return disc_map


def _determine_mandate_type_from_disclosures(disc_map: dict[str, Any]) -> str:
    """Determine mandate type from L2 disclosures."""
    checkout_disc = disc_map.get("checkout", {})
    intent_disc = disc_map.get("intent", {})
    if not isinstance(intent_disc, dict):
        intent_disc = {}
    constraints_disc = intent_disc.get("constraints", {})
    if not isinstance(constraints_disc, dict):
        constraints_disc = {}
    has_checkout = bool(checkout_disc)
    has_constraints = bool(constraints_disc)
    mandate_info = disc_map.get("mandate_info", {})
    if not isinstance(mandate_info, dict):
        mandate_info = {}
    if has_checkout and not has_constraints:
        return MandateType.IMMEDIATE.value
    elif has_constraints:
        return MandateType.AUTONOMOUS.value
    else:
        return mandate_info.get("type", MandateType.AUTONOMOUS.value)


def _build_create_mandate_input(
    disc_map: dict[str, Any], session: dict[str, Any],
    session_id: str, mandate_id: str, mandate_type: str,
) -> dict[str, Any]:
    """Build create mandate input dict from L2 disclosures for calling mandate.py."""
    mandate_info = disc_map.get("mandate_info", {})
    if not isinstance(mandate_info, dict):
        mandate_info = {}
    token_info = disc_map.get("token_info", {})
    if not isinstance(token_info, dict):
        token_info = {}
    intent_disc = disc_map.get("intent", {})
    if not isinstance(intent_disc, dict):
        intent_disc = {}
    checkout_disc = disc_map.get("checkout", {})
    if not isinstance(checkout_disc, dict):
        checkout_disc = {}

    description = mandate_info.get("description", intent_disc.get("desc", ""))
    raw = mandate_info.get("raw", intent_disc.get("raw", ""))
    token = token_info.get("token", session.get("token_id", ""))

    create_input: dict[str, Any] = {
        "tspSessionId": session_id,
        "mandateId": mandate_id,
        "token": token,
        "mandateType": mandate_type,
        "description": description,
        "raw": raw,
        "expiryTime": mandate_info.get("mandate_expiry_time", datetime.now(timezone.utc).isoformat()),
    }

    # IMMEDIATE: compute checkout_hash and set budget from checkout total_amount
    if mandate_type == MandateType.IMMEDIATE.value and checkout_disc:
        create_input["checkoutHash"] = _compute_checkout_hash(checkout_disc)
        ta = checkout_disc.get("total_amount", checkout_disc.get("totalAmount", {}))
        if ta:
            create_input["budgetAmount"] = {
                "cent": ta.get("amount", ta.get("cent", 0)),
                "currency": ta.get("currency", "USD"),
                "value": str(ta.get("value", ta.get("amount", 0))),
            }

    # AUTONOMOUS: set constraints and budget from L2 intent disclosure
    if mandate_type == MandateType.AUTONOMOUS.value:
        constraints_disc = intent_disc.get("constraints", {})
        if not isinstance(constraints_disc, dict):
            constraints_disc = {}
        if constraints_disc:
            budget_amount = constraints_disc.get("budget_amount", constraints_disc.get("budgetAmount", {}))
            merchant_names = constraints_disc.get("merchant_name_list", constraints_disc.get("merchantNameList", []))
            merchant_mccs = constraints_disc.get("merchant_mcc_list", constraints_disc.get("merchantMccList", []))
            if budget_amount:
                create_input["budgetAmount"] = {
                    "cent": budget_amount.get("amount", budget_amount.get("cent", 0)),
                    "currency": budget_amount.get("currency", "USD"),
                    "value": str(budget_amount.get("value", budget_amount.get("amount", 0))),
                }
            if merchant_names or merchant_mccs:
                create_input["constraints"] = {
                    "merchantNameList": merchant_names if isinstance(merchant_names, list) else [],
                    "merchantMccList": merchant_mccs if isinstance(merchant_mccs, list) else [],
                }

    return create_input


def _extract_checkout_for_storage(disc_map: dict[str, Any], mandate_type: str) -> dict:
    """Extract checkout data for storage from L2 disclosures."""
    if mandate_type == MandateType.IMMEDIATE.value:
        return disc_map.get("checkout", {})
    return {}


# -- applyCredential helpers --

def _verify_credential_chain(body: ApplyCredentialBody) -> None:
    """Verify SD-JWT credential chain with L1/L2 backend storage consistency check.

    Steps:
        1. Look up stored L1 from token record, verify request L1 matches
        2. Look up stored L2 from mandate record, verify request L2 matches
        3. Perform SD-JWT chain verification using stored L1/L2 + request L3

    This prevents frontend spoofing — request L1/L2 must match server-side records.
    """
    # Step 1: Verify L1 against stored token record
    token_record = _tokens.get_by_token_id(body.tokenId)
    _not_none(
        token_record,
        ResultCode.PARAM_ILLEGAL,
        f"token not found, tokenId={body.tokenId}",
    )
    assert token_record is not None
    stored_l1 = token_record.get("l1_serialized", "")
    _is_true(
        stored_l1 and stored_l1 == body.l1Serialized,
        ResultCode.PARAM_ILLEGAL,
        "L1 in request does not match stored token record",
    )

    # Step 2: Verify L2 against stored mandate record
    mandate_record = _tokens.get_by_mandate_id(body.mandateId)
    _not_none(
        mandate_record,
        ResultCode.PARAM_ILLEGAL,
        f"mandate not found, mandateId={body.mandateId}",
    )
    assert mandate_record is not None
    stored_l2 = mandate_record.get("l2_serialized", "")
    _is_true(
        stored_l2 and stored_l2 == body.l2Serialized,
        ResultCode.PARAM_ILLEGAL,
        "L2 in request does not match stored mandate record",
    )

    # Step 3: Verify SD-JWT chain using stored L1/L2 + request L3
    if body.l3Serialized:
        chain_result = verify_agent_chain(
            l1_serialized=stored_l1,
            l2_serialized=stored_l2,
            l3_serialized=body.l3Serialized,
            alipayplus_public_key=_jwk_mod.JWK(**get_aplus_public_jwk()),
            expected_iss=EXPECTED_L1_ISS,
            expected_l2_aud=EXPECTED_L2_AUD,
            expected_l3_aud=EXPECTED_L3_AUD,
        )
    else:
        chain_result = verify_credential_chain(
            l1_serialized=stored_l1,
            l2_serialized=stored_l2,
            alipayplus_public_key=_jwk_mod.JWK(**get_aplus_public_jwk()),
            expected_iss=EXPECTED_L1_ISS,
            expected_l2_aud=EXPECTED_L2_AUD,
        )
    if not chain_result.get("valid"):
        chain_errors = chain_result.get("errors", [])
        raise NetworkServiceException(
            ResultCode.PARAM_ILLEGAL,
            f"chain verification failed: {', '.join(chain_errors) if chain_errors else chain_result.get('error', 'unknown')}",
        )


if __name__ == "__main__":
    import uvicorn
    from common.log_config import uvicorn_log_config
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("ALIPAYPLUS_NETWORK_PORT", "8001")), log_level="warning", log_config=uvicorn_log_config())
