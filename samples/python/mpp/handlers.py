"""MPP business logic handlers and crypto helpers."""

from __future__ import annotations

import logging
import os
import pathlib
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    from .config import (
        MPP_PSP_ID,
        MPP_WALLET_NAME,
        AUTH_IN_PROCESS,
        AUTH_SUCCESS,
        AUTH_FAILED,
        ResultCode,
    )
    from .models import (
        CreateAuthorizationBody,
        InquiryAuthorizationBody,
        PayBody,
    )
    from .store import MppStore
    from .alipayplus_client import AlipayPlusClient
except ImportError:
    from config import (
        MPP_PSP_ID,
        MPP_WALLET_NAME,
        AUTH_IN_PROCESS,
        AUTH_SUCCESS,
        AUTH_FAILED,
        ResultCode,
    )
    from models import (
        CreateAuthorizationBody,
        InquiryAuthorizationBody,
        PayBody,
    )
    from store import MppStore
    from alipayplus_client import AlipayPlusClient

# Ensure project src/python/ (mandate_chain / common) and samples/python/
# (secret) are on sys.path.
_project_root = pathlib.Path(__file__).resolve().parents[3]
_src_python = str(_project_root / "src" / "python")
_samples_python = str(_project_root / "samples" / "python")
for _p in (_src_python, _samples_python):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from secret import get_mpp_private_key, get_mpp_public_jwk, get_mpp_kid

logger = logging.getLogger("mpp.server")


# ---------------------------------------------------------------------------
# Handler: createAuthorization
# ---------------------------------------------------------------------------


def handle_create_authorization(
    body: CreateAuthorizationBody, store: MppStore, client: AlipayPlusClient
) -> dict:
    auth_id = f"mpp-auth-{uuid.uuid4().hex[:8]}"
    session: dict[str, Any] = {
        "auth_id": auth_id,
        "auth_session_id": body.authSessionId,
        "agent_id": body.agentId,
        "customer_id": body.customerId,
        "auth_context": list(body.authContext),
        "intent": body.intent.model_dump() if body.intent else {},
        "checkout": body.checkout.model_dump() if body.checkout else {},
        "l1_serialized": body.l1Serialized or "",
        "status": AUTH_IN_PROCESS,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "l2_serialized": "",
        "idv_time": "",
        "agent_public_key_jwk": {},
        "agent_private_key_pem": "",
        "mandate_id": "",
        "mandate_type": "",
    }
    store.put_session(body.authSessionId, session)
    logger.debug(
        "[MPP] createAuthorization: session=%s, ctx=%s",
        body.authSessionId,
        body.authContext,
    )

    # In deferred mode (web demo), IDV waits for external /completeIdv trigger.
    # In auto mode (CLI demo), IDV auto-completes after 0.5s.
    idv_deferred = os.environ.get("IDV_DEFERRED", "").lower() in ("1", "true", "yes")
    if not idv_deferred:
        t = threading.Timer(0.5, _auto_complete_idv, args=[body.authSessionId, store, client])
        t.daemon = True
        t.start()

    auth_url = f"https://mpp.demo/auth?authId={auth_id}&sessionId={body.authSessionId}"
    return _ok({"authId": auth_id})


# ---------------------------------------------------------------------------
# Handler: inquiryAuthorization
# ---------------------------------------------------------------------------


def handle_inquiry_authorization(body: InquiryAuthorizationBody, store: MppStore) -> dict:
    session = store.get_session(body.authSessionId)
    if not session:
        return _fail(ResultCode.SESSION_NOT_FOUND, f"session not found: {body.authSessionId}")
    if session.get("auth_id") != body.authId:
        return _fail(ResultCode.PARAM_ILLEGAL, "authId does not match")

    auth_status = session.get("status", AUTH_IN_PROCESS)
    resp_data: dict[str, Any] = {
        "authId": body.authId,
        "authSessionId": body.authSessionId,
        "authStatus": auth_status,
        "authType": "AgenticPay",
        "walletAccountInfo": {
            "pspId": MPP_PSP_ID,
            "pspUserId": f"user-{(session.get('customer_id') or 'demo')[:8]}",
            "walletName": MPP_WALLET_NAME,
        },
    }

    if auth_status == AUTH_SUCCESS:
        is_mandate = "MANDATE" in session.get("auth_context", [])
        if is_mandate:
            resp_data["assuranceData"] = {
                "l2Serialized": session.get("l2_serialized", ""),
                "idvResult": "FACE",
                "idvTime": session.get("idv_time", ""),
                "mandateInfo": {
                    "mandateId": session.get("mandate_id", ""),
                    "mandateType": session.get("mandate_type", "AGENTIC_PAY"),
                    "mandateStatus": "ACTIVE",
                    "mandateExpiryTime": session.get("intent", {}).get("expireTime") or (
                        datetime.now(timezone.utc) + timedelta(days=365)
                    ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
            }
        else:
            resp_data["assuranceData"] = {
                "ispPk": get_mpp_public_jwk(),
                "ispKid": get_mpp_kid(),
                "idvResult": "FACE",
                "idvTime": session.get("idv_time", ""),
                "customerId": session.get("customer_id", ""),
                "pspId": MPP_PSP_ID,
                "tokenExpiryTime": session.get("intent", {}).get("expireTime") or (
                    datetime.now(timezone.utc) + timedelta(days=365)
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

    return _ok(resp_data)


# ---------------------------------------------------------------------------
# Handler: pay
# ---------------------------------------------------------------------------


def handle_pay(body: PayBody, store: MppStore) -> dict:
    record = store.get_payment_token(body.paymentToken)
    psp_user_id = record.get("psp_user_id", "user-demo") if record else "user-demo"
    logger.debug("[MPP] pay: token=%s...", body.paymentToken[:16])
    return _ok({"pspId": MPP_PSP_ID, "pspUserId": psp_user_id, "payResult": "SUCCESS"})


# ---------------------------------------------------------------------------
# Background: auto-complete IDV simulation
# ---------------------------------------------------------------------------


def _auto_complete_idv(
    auth_session_id: str, store: MppStore, client: AlipayPlusClient
) -> None:
    """Background thread: simulate user IDV, generate L2, notify AlipayPlus."""
    session = store.get_session(auth_session_id)
    if not session:
        return

    idv_time = datetime.now(timezone.utc).isoformat()
    is_mandate = "MANDATE" in session.get("auth_context", [])

    try:
        if is_mandate:
            mandate_id = f"mandate-{uuid.uuid4().hex[:8]}"
            l2, agent_pub_jwk, agent_priv_pem, mandate_type = _generate_l2(
                session=session,
                isp_key=get_mpp_private_key(),
                isp_kid=get_mpp_kid(),
                idv_time=idv_time,
                mandate_id=mandate_id,
            )
            store.update_session(
                auth_session_id,
                l2_serialized=l2,
                agent_public_key_jwk=agent_pub_jwk,
                agent_private_key_pem=agent_priv_pem,
                mandate_id=mandate_id,
                mandate_type=mandate_type,
                idv_time=idv_time,
                status=AUTH_SUCCESS,
            )
        else:
            store.update_session(
                auth_session_id,
                idv_time=idv_time,
                status=AUTH_SUCCESS,
            )

        _notify_alipayplus(auth_session_id, store, client)

    except Exception:
        logger.exception("[MPP] auto_complete_idv failed: session=%s", auth_session_id)
        store.update_session(auth_session_id, status=AUTH_FAILED)


# ---------------------------------------------------------------------------
# Handler: completeIdv (external trigger — simulates User biometric at MPP)
# ---------------------------------------------------------------------------

_IDV_DELAY_SECONDS = 5  # Simulated biometric verification duration


def handle_complete_idv(auth_session_id: str, store: MppStore, client: AlipayPlusClient) -> dict:
    """Externally triggered IDV completion. Blocks for 5s to simulate biometric."""
    session = store.get_session(auth_session_id)
    if not session:
        return _fail(ResultCode.SESSION_NOT_FOUND, f"session not found: {auth_session_id}")
    if session.get("status") != AUTH_IN_PROCESS:
        return _fail(ResultCode.PARAM_ILLEGAL, f"session not in IDV-pending state: {session.get('status')}")

    logger.debug("[MPP] completeIdv: session=%s, simulating %.1fs biometric...", auth_session_id, _IDV_DELAY_SECONDS)
    time.sleep(_IDV_DELAY_SECONDS)

    # Perform the same completion logic as auto_complete_idv
    _auto_complete_idv(auth_session_id, store, client)

    final = store.get_session(auth_session_id)
    if final and final.get("status") == AUTH_SUCCESS:
        return _ok({"authSessionId": auth_session_id, "idvResult": "PASS"})
    return _fail(ResultCode.SYSTEM_ERROR, "IDV completion failed")


def _notify_alipayplus(
    auth_session_id: str, store: MppStore, client: AlipayPlusClient
) -> None:
    session = store.get_session(auth_session_id)
    if not session or session.get("status") not in (AUTH_SUCCESS, AUTH_FAILED):
        return

    auth_status = session["status"]
    is_mandate = "MANDATE" in session.get("auth_context", [])

    payload: dict[str, Any] = {
        "sessionId": auth_session_id,
        "idvResult": "true",
        "idvTime": session.get("idv_time", ""),
    }

    if auth_status == AUTH_SUCCESS:
        if is_mandate:
            payload["l2Serialized"] = session.get("l2_serialized", "")
        else:
            payload["ispPk"] = get_mpp_public_jwk()
            payload["ispKid"] = get_mpp_kid()
            payload["customerId"] = session.get("customer_id", "")
            payload["pspId"] = MPP_PSP_ID
            intent_data = session.get("intent") or {}
            payload["tokenExpiryTime"] = intent_data.get("expireTime") or (
                datetime.now(timezone.utc) + timedelta(days=365)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
            payload["walletAccountInfo"] = {
                "pspId": MPP_PSP_ID,
                "pspUserId": f"user-{(session.get('customer_id') or 'demo')[:8]}",
                "walletName": MPP_WALLET_NAME,
            }

    client.notify_idv_result(payload)


# ---------------------------------------------------------------------------
# Crypto helpers
# ---------------------------------------------------------------------------


def _autonomous_exp_seconds(expire_time: str) -> int:
    """Seconds from now until the user-specified mandate expiry (AUTONOMOUS L2).

    The expiry is the one the user entered in the Shopping Agent for the
    human-not-present flow; there is deliberately no default, so a missing,
    malformed or already-passed value fails the L2 generation.
    """
    if not expire_time:
        raise ValueError(
            "intent.expireTime is required for an AUTONOMOUS mandate "
            "(user-specified expiry, no default)"
        )
    try:
        expiry = datetime.fromisoformat(expire_time.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid intent.expireTime: {expire_time!r}") from exc
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    exp_seconds = int((expiry - datetime.now(timezone.utc)).total_seconds())
    if exp_seconds <= 0:
        raise ValueError(f"intent.expireTime has already passed: {expire_time}")
    return exp_seconds


def _generate_l2(
    *,
    session: dict[str, Any],
    isp_key: Any,
    isp_kid: str,
    idv_time: str,
    mandate_id: str = "",
) -> tuple[str, dict, str, str]:
    """Generate L2 SD-JWT for a MANDATE session.

    Returns (l2_serialized, agent_pub_jwk, agent_priv_pem, mandate_type).
    mandate_type is "AUTONOMOUS" when constraints are present, else "IMMEDIATE".
    """
    from mandate_chain import generate_key_pair, public_jwk_dict
    from mandate_chain import create_immediate_layer2, create_autonomous_layer2

    intent_data = session.get("intent") or {}
    checkout_data = session.get("checkout") or {}
    constraints_data = intent_data.get("constraints") if intent_data else None

    has_checkout = bool(
        checkout_data
        and (checkout_data.get("totalAmount") or checkout_data.get("total_amount"))
    )
    has_constraints = bool(constraints_data)

    intent_raw = intent_data.get("raw") or "Shopping agent payment"
    intent_desc = intent_data.get("desc") or "User authorized payment"

    # Determine mode before building mandate_info so the type is correct in the L2 payload.
    mandate_type = "IMMEDIATE" if (has_checkout and not has_constraints) else "AUTONOMOUS"

    # AUTONOMOUS: the mandate lives exactly as long as the expiry the user
    # entered in the Shopping Agent — required, never defaulted here.
    # IMMEDIATE mandates are single-use and closed right after the payment.
    if mandate_type == "AUTONOMOUS":
        intent_expire_time = intent_data.get("expireTime") or ""
        exp_seconds = _autonomous_exp_seconds(intent_expire_time)
        mandate_expiry_time = intent_expire_time
    else:
        exp_seconds = 0
        mandate_expiry_time = intent_data.get("expireTime") or (
            datetime.now(timezone.utc) + timedelta(days=365)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

    token_info = {
        "token_unique_reference": session.get("auth_session_id", ""),
        "token_status": "ACTIVE",
        "user_login_id": f"user-{(session.get('customer_id') or 'demo')[:8]}",
        "wallet_name": MPP_WALLET_NAME,
    }
    mandate_info = {
        "mandate_id": mandate_id or f"mandate-{uuid.uuid4().hex[:8]}",
        "mandate_type": mandate_type,
        "mandate_status": "ACTIVE",
        "mandate_expiry_time": mandate_expiry_time,
    }

    # Agent key pair from centralized secret store — shared across all services
    from secret import get_agent_private_key, get_agent_public_jwk
    agent_jwk_obj = get_agent_private_key()  # jwk.JWK object
    agent_pub_jwk = get_agent_public_jwk()
    agent_priv_pem = ""

    if has_checkout and not has_constraints:
        intent = {"raw": intent_raw, "desc": intent_desc}
        l2 = create_immediate_layer2(
            l1_serialized=session.get("l1_serialized", ""),
            idv_result="FACE",
            idv_time=idv_time,
            intent=intent,
            token_info=token_info,
            mandate_info=mandate_info,
            checkout=_to_chain_checkout(checkout_data),
            private_key=isp_key,
            kid=isp_kid,
            aud="alipayplus.com",
        )
    else:
        intent = {
            "raw": intent_raw,
            "desc": intent_desc,
            "expiry_time": mandate_expiry_time,
        }
        if constraints_data:
            intent["constraints"] = _to_chain_constraints(constraints_data)
        l2 = create_autonomous_layer2(
            l1_serialized=session.get("l1_serialized", ""),
            idv_result="FACE",
            idv_time=idv_time,
            intent=intent,
            token_info=token_info,
            mandate_info=mandate_info,
            agent_public_key=agent_jwk_obj,
            private_key=isp_key,
            kid=isp_kid,
            aud="alipayplus.com",
            exp_seconds=exp_seconds,
        )

    return l2, agent_pub_jwk, agent_priv_pem, mandate_type


def _to_chain_checkout(checkout: dict) -> dict:
    """Convert camelCase checkout dict to mandate_chain snake_case format.

    Already-snake_case dicts (sent by AP's _to_chain_checkout) are passed through unchanged.
    """
    if "total_amount" in checkout:
        return checkout
    total = checkout.get("totalAmount") or {}
    merchant = checkout.get("merchant") or {}
    result: dict[str, Any] = {
        "total_amount": {
            "currency": total.get("currency", "USD"),
            "amount": total.get("cent", total.get("amount", 0)),
        },
        "merchant": {
            "reference_merchant_id": merchant.get(
                "referenceMerchantId", merchant.get("merchantId", "")
            ),
            "merchant_name": merchant.get("merchantName", ""),
            "merchant_mcc": merchant.get("merchantMCC", merchant.get("merchantMcc", "")),
        },
    }
    if checkout.get("goods"):
        result["goods"] = checkout["goods"]
    return result


def _to_chain_constraints(constraints: dict) -> dict:
    """Convert camelCase constraints dict to mandate_chain snake_case format."""
    budget = (
        constraints.get("budgetAmount") or constraints.get("budget_amount") or {}
    )
    return {
        "budget_amount": {
            "currency": budget.get("currency", "USD"),
            "amount": budget.get("cent", budget.get("amount", 0)),
        },
        "merchant_name_list": constraints.get(
            "merchantNameList", constraints.get("merchant_name_list", [])
        ),
        "merchant_mcc_list": constraints.get(
            "merchantMccList", constraints.get("merchant_mcc_list", [])
        ),
    }


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------


def _ok(data: dict[str, Any] | None = None) -> dict[str, Any]:
    resp: dict[str, Any] = {
        "result": {"resultCode": "SUCCESS", "resultStatus": "S", "resultMessage": "success"}
    }
    if data:
        resp.update(data)
    return resp


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"result": {"resultCode": code, "resultStatus": "F", "resultMessage": message}}
