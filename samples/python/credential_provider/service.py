"""Credential Provider — Core service implementing the CP integrator contract.

Role: shopping-agent → credential-provider (integrator) → AlipayPlus

The flow is asynchronous on the AlipayPlus side:
  1. CP accepts an initiate request, generates its own cp session_id
     (cps-xxx), calls AlipayPlus /createAuthorization → gets the downstream
     session_id + auth_url; AlipayPlus orchestrates the wallet MPP, which
     completes IDV out-of-band.
  2. AlipayPlus calls back CP /credential-provider/notifyAuthorization with
     the result (ENROLLMENT → token_id + L1; MANDATE → mandate_id + L2).
  3. CP correlates the callback via downstream_session_id, persists the
     result into CpStore, and marks the cp session COMPLETED.

Upstream contract (session-driven, all POST, role path: /credential-provider):
    1. POST /credential-provider/addPaymentMethod        — Trigger ENROLLMENT flow → session_id
    2. POST /credential-provider/queryPaymentMethodList  — Query bound payment methods (collection)
    3. POST /credential-provider/notifyAuthorization     — AlipayPlus→CP unified authorization callback
    4. POST /credential-provider/createMandateSession    — Trigger MANDATE flow → session_id
    5. POST /credential-provider/inquiryMandateSession   — Query mandate session by session_id
    6. (outbound) createAuthorization — CP→AlipayPlus, encapsulated in client.py
    7. POST /credential-provider/applyCredential         — session_id + L1+L2(+L3) → payment_token

Every response from an initiate endpoint carries {session_id, status};
status is PENDING_IDV (web mode) or COMPLETED (CLI mode, which blocks until
the callback arrives, bounded by _CALLBACK_TIMEOUT). Follow-up queries are
strict: they require the session_id and never fall back to "latest record".
"""
from __future__ import annotations

import logging
import os
import json
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import sys, pathlib
_project_root = pathlib.Path(__file__).resolve().parents[3]
_src_python = str(_project_root / "src" / "python")
if _src_python not in sys.path:
    sys.path.insert(0, _src_python)

import httpx

from common.multi_currency_money import MultiCurrencyMoney
from models import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING_IDV,
    AddPaymentMethodRequest,
    AddPaymentMethodResponse,
    ApplyCredentialRequest,
    ApplyCredentialResponse,
    CreateMandateSessionRequest,
    CreateMandateSessionResponse,
    IdvInfo,
    InquiryMandateSessionRequest,
    InquiryMandateSessionResponse,
    NotifyAuthorizationRequest,
    NotifyAuthorizationResponse,
    PaymentMethod,
    QueryPaymentMethodListRequest,
    QueryPaymentMethodListResponse,
)
from stores import CpStore
from client import AlipayPlusClient
from common.utils import generate_agent_id

logger = logging.getLogger("cp.server")

# -------------------------------------------------------------------------
# Configuration & shared instances
# -------------------------------------------------------------------------

_client = AlipayPlusClient()
_cp_store = CpStore()

# CP identity sent to AlipayPlus (stable per process; demo scope)
_CP_ID = f"cp-{uuid.uuid4().hex[:6]}"

# How long the initiate endpoints wait for the AlipayPlus callback.
# MPP auto-completes IDV in ~0.5s, so this is a generous upper bound.
_CALLBACK_TIMEOUT: float = 15.0

# Default AUTONOMOUS mandate constraints (demo defaults)
_DEFAULT_BUDGET: MultiCurrencyMoney = MultiCurrencyMoney.of(200000, "USD")
_DEFAULT_MERCHANT_NAMES: list[str] = ["Demo Store"]
_DEFAULT_MERCHANT_MCCS: list[str] = ["5411"]

# Blocking events for CLI-mode initiate calls, keyed by the DOWNSTREAM
# (AlipayPlus) session id because that is what the callback carries.
# Session state itself lives in CpStore (cp_session table); this dict only
# holds the threading.Event used to wake up a blocked initiate call.
_pending_events: dict[str, threading.Event] = {}
_pending_lock = threading.Lock()


# -------------------------------------------------------------------------
# Internal helpers: session ids & callback blocking
# -------------------------------------------------------------------------

def _new_session_id() -> str:
    """Generate a CP-owned session id (upstream contract key)."""
    return f"cps-{uuid.uuid4().hex[:12]}"


def _register_event(downstream_session_id: str) -> None:
    """Register a wake-up event for a CLI-mode blocking initiate call."""
    with _pending_lock:
        _pending_events[downstream_session_id] = threading.Event()


def _signal_event(downstream_session_id: str) -> None:
    """Wake up the initiate call blocked on this downstream session (if any)."""
    with _pending_lock:
        event = _pending_events.get(downstream_session_id)
    if event is not None:
        event.set()


def _wait_for_callback(downstream_session_id: str, timeout: float = _CALLBACK_TIMEOUT) -> bool:
    """Block until the AlipayPlus callback for this downstream session arrives.

    Returns True when the callback fired, False on timeout. The event entry
    is removed only on success so retries stay possible.
    """
    with _pending_lock:
        event = _pending_events.get(downstream_session_id)
    if event is None:
        return False
    if not event.wait(timeout):
        return False
    with _pending_lock:
        _pending_events.pop(downstream_session_id, None)
    return True


def _extract_auth_url(data: dict[str, Any]) -> str:
    """Extract the wallet auth URL from a createAuthorization response.

    AlipayPlus nests it as data.passkey_options.authUrl (MPP camelCase).
    """
    passkey = data.get("passkeyOptions") or {}
    return passkey.get("authUrl", "")


def _assemble_mandate(mandate_id: str) -> Optional[dict[str, Any]]:
    """Retrieve a mandate record and supplement the associated l1_serialized."""
    record = _cp_store.get_mandate(mandate_id)
    if record is None:
        return None
    # Mandate record does not contain l1_serialized; look up via token_id
    token_id = record.get("token_id", "")
    l1_serialized = ""
    if token_id:
        token_record = _cp_store.get_token(token_id)
        if token_record:
            l1_serialized = token_record.get("l1_serialized", "")
    return {
        "mandate_id": record.get("mandate_id", ""),
        "token_id": token_id,
        "l1_serialized": l1_serialized,
        "l2_serialized": record.get("l2_serialized", ""),
        "mandate_type": record.get("mandate_type", ""),
    }


# =========================================================================
# Interface 1: POST /addPaymentMethod
# Shopping Agent → CP: Trigger wallet ENROLLMENT flow
# =========================================================================

def add_payment_method(body: AddPaymentMethodRequest = AddPaymentMethodRequest()) -> AddPaymentMethodResponse:
    """Enrollment: bind wallet → L1 arrives via /credential-provider/notifyAuthorization.

    Flow: CP→AlipayPlus(createAuthorization ENROLLMENT) → [async IDV on MPP]
          → AlipayPlus→CP callback with token_id + L1 → stored in CpStore.
    Always blocks until the AlipayPlus callback arrives (sync mode),
    then returns {session_id, status=COMPLETED, token_id}.
    """
    agent_id = body.agentId or generate_agent_id()

    try:
        resp = _client.create_authorization(
            auth_context="ENROLLMENT",
            agent_id=agent_id,
            credential_provider_id=_CP_ID,
            wallet_name=body.walletName,
        )
    except httpx.HTTPError as e:
        return AddPaymentMethodResponse(success=False, error=f"AlipayPlus unreachable: {e}")
    if not resp.get("success"):
        return AddPaymentMethodResponse(
            success=False, error=resp.get("resultMessage", "createAuthorization failed"))

    data = resp.get("data") or {}
    downstream_session_id = data.get("sessionId", "")
    auth_url = _extract_auth_url(data)
    if not downstream_session_id:
        return AddPaymentMethodResponse(success=False, error="createAuthorization returned no session_id")

    # CP-owned session: the upstream contract key for all follow-up calls
    session_id = _new_session_id()
    _cp_store.save_session(
        session_id,
        auth_context="ENROLLMENT",
        status=STATUS_PENDING_IDV,
        downstream_session_id=downstream_session_id,
        auth_url=auth_url,
        wallet_name=body.walletName,
    )
    _register_event(downstream_session_id)

    # Web mode (IDV_DEFERRED=true): return immediately; User completes IDV at wallet (MPP).
    idv_deferred = os.environ.get("IDV_DEFERRED", "").lower() in ("1", "true", "yes")
    if idv_deferred:
        return AddPaymentMethodResponse(
            success=True,
            sessionId=session_id,
            status=STATUS_PENDING_IDV,
            idv=IdvInfo(authUrl=auth_url, authSessionId=downstream_session_id),
        )

    # CLI mode: wait for the AlipayPlus /credential-provider/notifyAuthorization callback (L1).
    if not _wait_for_callback(downstream_session_id):
        _cp_store.update_session(session_id, status=STATUS_FAILED, error="enrollment callback timeout")
        return AddPaymentMethodResponse(
            success=False,
            sessionId=session_id,
            status=STATUS_FAILED,
            error=f"Timed out waiting for enrollment callback (session {session_id})",
        )

    completed = _cp_store.get_session(session_id) or {}
    return AddPaymentMethodResponse(
        success=True,
        sessionId=session_id,
        status=STATUS_COMPLETED,
        tokenId=completed.get("token_id", ""),
    )


# =========================================================================
# Interface 2: POST /queryPaymentMethodList
# Shopping Agent → CP: Query registered payment methods
# =========================================================================

def query_payment_method_list(
    body: Optional[QueryPaymentMethodListRequest] = None,
) -> QueryPaymentMethodListResponse:
    """Query bound payment methods — always returns a collection.

    Filters (all optional): session_id narrows to the token produced by that
    enrollment session; wallet_name / token_id filter the full list. Without
    filters, every bound method is returned.

    NOTE: Only tokens with a non-empty l1_serialized are returned. An empty
    l1_serialized means the enrollment callback has not arrived yet, so the
    token must not be exposed to the shopping agent.
    """
    # session_id filter: strict lookup through the cp_session table
    if body and body.sessionId:
        session = _cp_store.get_session(body.sessionId)
        if session is None:
            return QueryPaymentMethodListResponse(
                success=False, error=f"Session '{body.sessionId}' not found.")
        if session.get("auth_context") != "ENROLLMENT":
            return QueryPaymentMethodListResponse(
                success=False,
                error=f"Session '{body.sessionId}' is not an enrollment session.")
        if session.get("status") != STATUS_COMPLETED:
            return QueryPaymentMethodListResponse(
                success=False,
                error=f"Session '{body.sessionId}' is {session.get('status')}; "
                      f"IDV has not completed yet.")
        token = _cp_store.get_token(session.get("token_id", ""))
        if not token or not token.get("l1_serialized"):
            return QueryPaymentMethodListResponse(
                success=False,
                error=f"Session '{body.sessionId}' completed but its token/L1 is missing.")
        records = [token]
    else:
        records = [t for t in _cp_store.list_tokens() if t.get("l1_serialized")]

    if body and body.tokenId:
        records = [t for t in records if t.get("token_id") == body.tokenId]
    if body and body.walletName:
        records = [t for t in records if t.get("wallet_name") == body.walletName]

    methods = []
    for t in records:
        # wallet_account_info is stored as a JSON string; extract the wallet
        # user login id (pspUserId) so the agent/frontend can display it.
        wai_raw = t.get("wallet_account_info") or ""
        try:
            wai = json.loads(wai_raw) if wai_raw else {}
        except (ValueError, TypeError):
            wai = {}
        methods.append(PaymentMethod(
            tokenId=t["token_id"],
            walletName=t.get("wallet_name", ""),
            userLoginId=wai.get("pspUserId", ""),
            l1Serialized=t.get("l1_serialized", ""),
            gmtCreate=t.get("gmt_create") or "",
        ))
    return QueryPaymentMethodListResponse(success=True, paymentMethods=methods)


# =========================================================================
# Interface 3: POST /credential-provider/notifyAuthorization
# AlipayPlus → CP: Unified authorization callback
# =========================================================================

def notify_authorization(body: NotifyAuthorizationRequest) -> NotifyAuthorizationResponse:
    """Unified callback from AlipayPlus when authorization completes.

    ENROLLMENT → persist token (token_id + L1); MANDATE → persist mandate
    (mandate_id + L2). Context is auto-inferred when absent. The cp session
    is correlated via downstream_session_id, updated to COMPLETED with the
    result ids, then any blocked initiate call is woken up.
    """
    if not body.sessionId:
        return NotifyAuthorizationResponse(success=False, error="Missing required field: session_id")

    auth_context = body.authContext
    if not auth_context:
        if body.tokenId:
            auth_context = "ENROLLMENT"
        elif body.mandateId:
            auth_context = "MANDATE"

    # Correlate the downstream session back to the cp session record
    cp_session = _cp_store.find_session_by_downstream_id(body.sessionId)
    if cp_session is None:
        logger.warning("[CP] callback for unknown downstream session %s", body.sessionId)

    if auth_context == "ENROLLMENT":
        if not body.tokenId:
            return NotifyAuthorizationResponse(success=False, error="ENROLLMENT callback requires token_id")
        if not body.l1Serialized:
            return NotifyAuthorizationResponse(success=False, error="ENROLLMENT callback requires l1_serialized")
        _cp_store.save_token(
            body.tokenId,
            l1_serialized=body.l1Serialized,
            session_id=cp_session.get("session_id", "") if cp_session else "",
            wallet_name=cp_session.get("wallet_name", "") if cp_session else "",
            wallet_account_info=body.walletAccountInfo,
        )
        if cp_session:
            _cp_store.update_session(
                cp_session["session_id"],
                status=STATUS_COMPLETED,
                token_id=body.tokenId,
            )
    elif auth_context == "MANDATE":
        if not body.mandateId:
            return NotifyAuthorizationResponse(success=False, error="MANDATE callback requires mandate_id")
        if not body.l2Serialized:
            return NotifyAuthorizationResponse(success=False, error="MANDATE callback requires l2_serialized")
        _cp_store.save_mandate(
            body.mandateId,
            token_id=body.tokenId or (cp_session.get("token_id", "") if cp_session else ""),
            l2_serialized=body.l2Serialized,
            session_id=cp_session.get("session_id", "") if cp_session else "",
            mandate_type=body.mandateType or (cp_session.get("mandate_type", "") if cp_session else ""),
        )
        if cp_session:
            _cp_store.update_session(
                cp_session["session_id"],
                status=STATUS_COMPLETED,
                mandate_id=body.mandateId,
            )
    else:
        return NotifyAuthorizationResponse(
            success=False,
            error="Cannot determine auth_context. Provide token_id (ENROLLMENT) or mandate_id (MANDATE).",
        )

    _signal_event(body.sessionId)
    return NotifyAuthorizationResponse(success=True)


# =========================================================================
# Interface 4: POST /credential-provider/createMandateSession
# Shopping Agent → CP: Create a mandate authorization session
# =========================================================================

def create_mandate_session(body: CreateMandateSessionRequest) -> CreateMandateSessionResponse:
    """Mandate: authorize intent → L2 arrives via /credential-provider/notifyAuthorization.

    token_id is REQUIRED and must reference a completed enrollment (strict —
    no fallback to "latest binding"). Flow: CP→AlipayPlus(createAuthorization
    MANDATE, passing token_id + intent) → [async IDV on
    MPP] → AlipayPlus→CP callback with mandate_id + L2 → stored in CpStore.
    agent_public_jwk is obtained from common.secret by MPP directly.

    Mode selection mirrors MPP's rule (checkout && !constraints → IMMEDIATE):
    when a checkout is supplied constraints are NOT defaulted, otherwise the
    session falls back to AUTONOMOUS with provided-or-default constraints.
    """
    if not body.intentRaw:
        return CreateMandateSessionResponse(success=False, error="Missing required field: intent_raw")
    if not body.tokenId:
        return CreateMandateSessionResponse(
            success=False,
            error="Missing required field: token_id. "
                  "Call /addPaymentMethod + /queryPaymentMethodList first.")

    binding = _cp_store.get_token(body.tokenId)
    if not binding or not binding.get("l1_serialized"):
        return CreateMandateSessionResponse(
            success=False,
            error=f"Token '{body.tokenId}' not found or its L1 is not ready. "
                  "Call /addPaymentMethod first.")
    token_id = body.tokenId

    agent_id = body.agentId or generate_agent_id()

    # IMMEDIATE when a checkout is present without constraints; otherwise
    # AUTONOMOUS (inject demo default constraints if the agent sent none).
    constraints = body.constraints
    if body.checkout and not constraints:
        expected_mandate_type = "IMMEDIATE"
    else:
        expected_mandate_type = "AUTONOMOUS"
        constraints = constraints or {
            "budgetAmount": {"cent": _DEFAULT_BUDGET.fetch_minor_units(), "currency": _DEFAULT_BUDGET.currency_code},
            "merchantNameList": _DEFAULT_MERCHANT_NAMES,
            "merchantMccList": _DEFAULT_MERCHANT_MCCS,
        }

    try:
        resp = _client.create_authorization(
            auth_context="MANDATE",
            agent_id=agent_id,
            credential_provider_id=_CP_ID,
            wallet_name=binding.get("wallet_name", ""),
            token_id=token_id,
            intent_raw=body.intentRaw,
            intent_expire_time=body.intentExpireTime or (datetime.now(timezone.utc) + timedelta(days=183)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            constraints=constraints,
            checkout=body.checkout,
        )
    except httpx.HTTPError as e:
        return CreateMandateSessionResponse(success=False, error=f"AlipayPlus unreachable: {e}")
    if not resp.get("success"):
        return CreateMandateSessionResponse(
            success=False, error=resp.get("resultMessage", "createAuthorization failed"))

    data = resp.get("data") or {}
    downstream_session_id = data.get("sessionId", "")
    auth_url = _extract_auth_url(data)
    if not downstream_session_id:
        return CreateMandateSessionResponse(success=False, error="createAuthorization returned no session_id")

    # CP-owned session: the upstream contract key for inquiry/applyCredential
    session_id = _new_session_id()
    _cp_store.save_session(
        session_id,
        auth_context="MANDATE",
        status=STATUS_PENDING_IDV,
        downstream_session_id=downstream_session_id,
        auth_url=auth_url,
        wallet_name=binding.get("wallet_name", ""),
        token_id=token_id,
        mandate_type=expected_mandate_type,
    )
    _register_event(downstream_session_id)

    # Web mode: return immediately; User completes IDV at the wallet (MPP).
    if body.deferIdv:
        return CreateMandateSessionResponse(
            success=True,
            sessionId=session_id,
            status=STATUS_PENDING_IDV,
            idv=IdvInfo(authUrl=auth_url, authSessionId=downstream_session_id),
        )

    # CLI mode: wait for the AlipayPlus /credential-provider/notifyAuthorization callback (L2).
    if not _wait_for_callback(downstream_session_id):
        _cp_store.update_session(session_id, status=STATUS_FAILED, error="mandate callback timeout")
        return CreateMandateSessionResponse(
            success=False,
            sessionId=session_id,
            status=STATUS_FAILED,
            error=f"Timed out waiting for mandate callback (session {session_id})",
        )

    completed = _cp_store.get_session(session_id) or {}
    return CreateMandateSessionResponse(
        success=True,
        sessionId=session_id,
        status=STATUS_COMPLETED,
        mandateId=completed.get("mandate_id", ""),
    )


# =========================================================================
# Interface 5: POST /inquiryMandateSession
# Shopping Agent → CP: Query mandate session state
# =========================================================================

def inquiry_mandate_session(body: Optional[InquiryMandateSessionRequest] = None) -> InquiryMandateSessionResponse:
    """Query mandate session state — strict lookup by cp session_id.

    PENDING_IDV sessions return status only (no packets); COMPLETED sessions
    return mandate_id + mandate_type + token_id + L1/L2 packets.
    """
    session_id = body.sessionId if body else None
    if not session_id:
        return InquiryMandateSessionResponse(
            success=False,
            error="Missing required field: session_id (from /createMandateSession).")

    session = _cp_store.get_session(session_id)
    if session is None:
        return InquiryMandateSessionResponse(
            success=False, error=f"Session '{session_id}' not found.")
    if session.get("auth_context") != "MANDATE":
        return InquiryMandateSessionResponse(
            success=False, error=f"Session '{session_id}' is not a mandate session.")

    status = session.get("status", "")
    if status != STATUS_COMPLETED:
        return InquiryMandateSessionResponse(
            success=True,
            sessionId=session_id,
            status=status,
            error=session.get("error") or None,
        )

    m = _assemble_mandate(session.get("mandate_id", ""))
    if not m:
        return InquiryMandateSessionResponse(
            success=False,
            error=f"Session '{session_id}' completed but its mandate record is missing.")
    return InquiryMandateSessionResponse(
        success=True,
        sessionId=session_id,
        status=STATUS_COMPLETED,
        mandateId=m["mandate_id"],
        mandateType=m.get("mandate_type", ""),
        tokenId=m.get("token_id", ""),
        l1Serialized=m.get("l1_serialized", ""),
        l2Serialized=m.get("l2_serialized", ""),
    )


# =========================================================================
# Interface 6: createAuthorization (outbound — NOT an HTTP endpoint on CP)
# =========================================================================
# Implemented in client.py (AlipayPlusClient.create_authorization); used by
# add_payment_method (ENROLLMENT) and create_mandate_session (MANDATE).


# =========================================================================
# Interface 7: POST /applyCredential
# Shopping Agent → CP: Submit L1+L2(+L3) for payment token
# =========================================================================

def apply_credential(body: ApplyCredentialRequest) -> ApplyCredentialResponse:
    """Submit L1+L2(+L3) for chain verification → get payment_token.

    session_id (the mandate session) is REQUIRED; CP resolves token_id +
    mandate_id from it, guaranteeing both belong to the same authorization
    flow. L3 is optional for IMMEDIATE mode (2-layer chain); AlipayPlus
    routes to the matching verifier when L3 is empty. Token/mandate expiry
    is enforced downstream by AlipayPlus.
    """
    if not body.sessionId:
        return ApplyCredentialResponse(
            success=False,
            error="Missing required field: session_id (from /createMandateSession).")
    if not body.l1Serialized:
        return ApplyCredentialResponse(success=False, error="Missing required field: l1_serialized")
    if not body.l2Serialized:
        return ApplyCredentialResponse(success=False, error="Missing required field: l2_serialized")

    session = _cp_store.get_session(body.sessionId)
    if session is None:
        return ApplyCredentialResponse(
            success=False, error=f"Session '{body.sessionId}' not found.")
    if session.get("auth_context") != "MANDATE":
        return ApplyCredentialResponse(
            success=False, error=f"Session '{body.sessionId}' is not a mandate session.")
    if session.get("status") != STATUS_COMPLETED:
        return ApplyCredentialResponse(
            success=False,
            error=f"Session '{body.sessionId}' is {session.get('status')}; "
                  "mandate authorization has not completed.")

    token_id = session.get("token_id", "")
    mandate_id = session.get("mandate_id", "")
    if not token_id or not mandate_id:
        return ApplyCredentialResponse(
            success=False,
            error=f"Session '{body.sessionId}' record is incomplete (token_id/mandate_id missing).")

    try:
        resp = _client.apply_credential(
            token_id=token_id,
            mandate_id=mandate_id,
            l1_serialized=body.l1Serialized,
            l2_serialized=body.l2Serialized,
            l3_serialized=body.l3Serialized or "",
            checkout=body.checkout,
        )
    except httpx.HTTPError as e:
        return ApplyCredentialResponse(success=False, error=f"AlipayPlus unreachable: {e}")

    if not resp.get("success"):
        return ApplyCredentialResponse(
            success=False,
            error=resp.get("resultMessage", "AlipayPlus applyCredential failed"))

    data = resp.get("data") or {}
    return ApplyCredentialResponse(
        success=True,
        paymentToken=data.get("paymentToken", ""),
        mandateType=data.get("mandateType"),
    )
