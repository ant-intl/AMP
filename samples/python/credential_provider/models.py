"""Credential Provider — Pydantic request/response models.

Defines typed models for the session-driven CP contract:
  Upstream  (Shopping Agent → CP): addPaymentMethod, queryPaymentMethodList,
            createMandateSession, inquiryMandateSession, applyCredential
  Downstream callback (AlipayPlus → CP): notifyAuthorization

Contract keys:
  - sessionId: CP-generated (cps-xxx), returned by every initiate endpoint
    and required by every follow-up call. The downstream AlipayPlus session
    id is an internal mapping and never acts as the upstream contract key.
  - status: unified session state — PENDING_IDV | COMPLETED | FAILED.
    Sync (CLI) and async (web) modes share the same response shape and only
    differ in the status value.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


# Session status values shared by all initiate/inquiry responses
STATUS_PENDING_IDV = "PENDING_IDV"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"


class IdvInfo(BaseModel):
    """Wallet-side IDV information passed through by CP (opaque to CP).

    Handed to the User so they can complete identity verification at their
    wallet (MPP). authSessionId is the wallet-side session used by the
    demo's /completeIdv simulation.
    """
    authUrl: str = ""
    authSessionId: str = ""


# ---------------------------------------------------------------------------
# Interface 1: POST /credential-provider/addPaymentMethod
# ---------------------------------------------------------------------------

class AddPaymentMethodRequest(BaseModel):
    """Shopping Agent → CP: register a new wallet payment method."""
    walletName: str = "ALIPAY_HK" # Target wallet (routes to the matching MPP)
    agentId: Optional[str] = None  # Optional caller identity


class AddPaymentMethodResponse(BaseModel):
    """Response for /addPaymentMethod."""
    success: bool
    sessionId: Optional[str] = None  # CP session id (contract key for follow-ups)
    status: Optional[str] = None      # PENDING_IDV | COMPLETED | FAILED
    tokenId: Optional[str] = None    # Present when status == COMPLETED
    idv: Optional[IdvInfo] = None     # Present when status == PENDING_IDV
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Interface 2: POST /credential-provider/queryPaymentMethodList
# ---------------------------------------------------------------------------

class PaymentMethod(BaseModel):
    """A single bound wallet payment method (L1 + wallet + token info)."""
    tokenId: str
    walletName: str = ""
    userLoginId: str = ""  # Wallet user login id (from walletAccountInfo.pspUserId)
    l1Serialized: str = ""
    gmtCreate: str = ""


class QueryPaymentMethodListRequest(BaseModel):
    """Shopping Agent → CP: query registered payment methods.

    All filters optional; without filters, every bound method is returned.
    sessionId narrows the result to the token produced by that enrollment
    session (the way an agent retrieves "its own" binding after IDV).
    """
    sessionId: Optional[str] = None   # Filter by enrollment session (optional)
    walletName: Optional[str] = None  # Filter by wallet name (optional)
    tokenId: Optional[str] = None     # Filter by specific token (optional)


class QueryPaymentMethodListResponse(BaseModel):
    """Response for /queryPaymentMethodList — always a collection."""
    success: bool = True
    paymentMethods: list[PaymentMethod] = []
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Interface 3: POST /credential-provider/notifyAuthorization
# Unified callback from AlipayPlus → CP
# ---------------------------------------------------------------------------

class NotifyAuthorizationRequest(BaseModel):
    """AlipayPlus → CP callback when authorization completes.

    For ENROLLMENT: carries tokenId + l1Serialized + walletAccountInfo
    For MANDATE: carries mandateId + l2Serialized
    sessionId here is the AlipayPlus (downstream) session id; CP maps it
    back to its own cp session via downstreamSessionId.
    """
    sessionId: str
    authContext: Optional[str] = None  # ENROLLMENT | MANDATE (auto-inferred if absent)
    tokenId: Optional[str] = None
    l1Serialized: Optional[str] = None
    mandateId: Optional[str] = None
    l2Serialized: Optional[str] = None
    mandateType: Optional[str] = None  # AUTONOMOUS | IMMEDIATE (optional)
    walletAccountInfo: Optional[dict[str, Any]] = None  # Wallet account details (ENROLLMENT only)


class NotifyAuthorizationResponse(BaseModel):
    """Response for /notifyAuthorization."""
    success: bool
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Interface 4: POST /credential-provider/createMandateSession
# ---------------------------------------------------------------------------

class CreateMandateSessionRequest(BaseModel):
    """Shopping Agent → CP: create a mandate authorization session.

    tokenId is REQUIRED — it must come from a prior /addPaymentMethod +
    /queryPaymentMethodList round trip. There is no fallback resolution.
    """
    tokenId: Optional[str] = None  # REQUIRED (validated in service for a friendly error)
    agentId: Optional[str] = None
    intentRaw: str = "Shopping agent: buy items for user"
    intentExpireTime: Optional[str] = None
    constraints: Optional[dict[str, Any]] = None  # AUTONOMOUS budget/merchant limits
    checkout: Optional[dict[str, Any]] = None  # Present for IMMEDIATE mode
    # True (web mode): return PENDING_IDV immediately; IDV completes externally at MPP.
    deferIdv: bool = False


class CreateMandateSessionResponse(BaseModel):
    """Response for /createMandateSession."""
    success: bool
    sessionId: Optional[str] = None  # CP session id (contract key for follow-ups)
    status: Optional[str] = None      # PENDING_IDV | COMPLETED | FAILED
    mandateId: Optional[str] = None  # Present when status == COMPLETED
    idv: Optional[IdvInfo] = None     # Present when status == PENDING_IDV
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Interface 5: POST /credential-provider/inquiryMandateSession
# ---------------------------------------------------------------------------

class InquiryMandateSessionRequest(BaseModel):
    """Shopping Agent → CP: query mandate session state.

    sessionId is REQUIRED — the CP session id from /createMandateSession.
    """
    sessionId: Optional[str] = None  # REQUIRED (validated in service for a friendly error)


class InquiryMandateSessionResponse(BaseModel):
    """Response for /inquiryMandateSession."""
    success: bool = True
    sessionId: Optional[str] = None
    status: Optional[str] = None      # PENDING_IDV | COMPLETED | FAILED
    mandateId: Optional[str] = None  # Fields below present when COMPLETED
    mandateType: Optional[str] = None
    tokenId: Optional[str] = None
    l1Serialized: Optional[str] = None
    l2Serialized: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Interface 7: POST /credential-provider/applyCredential
# ---------------------------------------------------------------------------

class ApplyCredentialRequest(BaseModel):
    """Shopping Agent → CP: apply for payment credential (L1+L2+L3 → token).

    sessionId is REQUIRED — the mandate session (from /createMandateSession);
    CP resolves tokenId + mandateId from that session, guaranteeing the pair
    belongs to the same authorization flow.
    """
    sessionId: Optional[str] = None  # REQUIRED (validated in service for a friendly error)
    l1Serialized: Optional[str] = None
    l2Serialized: Optional[str] = None
    l3Serialized: Optional[str] = None   # Optional for IMMEDIATE (2-layer chain)
    checkout: Optional[dict[str, Any]] = None


class ApplyCredentialResponse(BaseModel):
    """Response for /applyCredential."""
    success: bool = True
    paymentToken: Optional[str] = None
    mandateType: Optional[str] = None
    error: Optional[str] = None
