"""Credential Provider — outbound client encapsulation.

AlipayPlusClient: CP -> AlipayPlus calls
  - create_authorization  → POST /network/createAuthorization
  - apply_credential      → POST /network/applyCredential

CP no longer talks to MPP directly: AlipayPlus orchestrates MPP internally
(createAuthorization routes to the wallet's MPP; MPP auto-completes IDV
and notifies AlipayPlus, which then calls back CP with L1/L2 results).

service.py consumes this module via ``_client = AlipayPlusClient()``.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

from common.http_client import http_post

logger = logging.getLogger("cp.http-client")

# ---------------------------------------------------------------------------
# AlipayPlus base URL (network service runs as a separate process)
# ---------------------------------------------------------------------------
_ats_port = os.environ.get("ALIPAYPLUS_NETWORK_PORT", "8083")
_ATS_BASE_URL: str = os.environ.get("ATS_BASE_URL", f"http://localhost:{_ats_port}")


class AlipayPlusClient:
    """Outbound client for AlipayPlus service calls.

    Encapsulates the two CP → AlipayPlus contracts:
    /createAuthorization and /applyCredential.
    """

    def __init__(self, ats_base_url: str = _ATS_BASE_URL) -> None:
        self._ats_base_url = ats_base_url

    # --- createAuthorization ---
    # CP -> AlipayPlus: POST /network/createAuthorization

    def create_authorization(
        self,
        *,
        auth_context: str,
        agent_id: str,
        credential_provider_id: str,
        wallet_name: str = "",
        token_id: Optional[str] = None,
        intent_raw: Optional[str] = None,
        intent_expire_time: Optional[str] = None,
        constraints: Optional[dict[str, Any]] = None,
        checkout: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Create an authorization (IDV) session on AlipayPlus.

        Maps to user contract: /createAuthorization
        Actual downstream endpoint: POST /network/createAuthorization
        Used by: addPaymentMethod (ENROLLMENT) and createMandateSession (MANDATE)

        Returns the AlipayPlus envelope:
        {success, result_code, data: {session_id, auth_id,
         passkey_options, status}}
        """
        payload: dict[str, Any] = {
            "authContext": auth_context,
            "agentId": agent_id,
            "credentialProviderId": credential_provider_id,
        }
        if wallet_name:
            payload["walletName"] = wallet_name
        if token_id:
            payload["tokenId"] = token_id
        if intent_raw:
            payload["intentRaw"] = intent_raw
        if intent_expire_time:
            payload["intentExpireTime"] = intent_expire_time
        if constraints:
            payload["constraints"] = constraints
        if checkout:
            payload["checkout"] = checkout

        logger.debug("[CP->AlipayPlus] create_authorization auth_context=%s agent=%s",
                    auth_context, agent_id)
        resp = http_post(f"{self._ats_base_url}/network/createAuthorization",
                         json=payload, logger_name="cp.http-client")
        return resp.json()

    # --- applyCredential ---
    # CP -> AlipayPlus: POST /network/applyCredential

    def apply_credential(
        self,
        *,
        token_id: str,
        mandate_id: str,
        l1_serialized: str,
        l2_serialized: str,
        l3_serialized: str,
        checkout: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Submit the L1+L2(+L3) chain to AlipayPlus for verification and
        payment token issuance.

        Actual downstream endpoint: POST /network/applyCredential
        """
        logger.debug("[CP->AlipayPlus] apply_credential token=%s mandate=%s",
                    token_id, mandate_id)
        payload: dict[str, Any] = {
            "tokenId": token_id,
            "mandateId": mandate_id,
            "l1Serialized": l1_serialized,
            "l2Serialized": l2_serialized,
            "l3Serialized": l3_serialized,
        }
        if checkout:
            payload["checkout"] = checkout
        resp = http_post(f"{self._ats_base_url}/network/applyCredential",
                         json=payload, logger_name="cp.http-client")
        return resp.json()
