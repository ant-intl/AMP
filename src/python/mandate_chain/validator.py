"""AMP Mandate Chain - Validator.

Verifies the three-layer SD-JWT authorization chain:
  L1: Verify A+ signature, extract ISP public key from cnf.jwk
  L2: Verify sd_hash binding to L1, verify ISP signature, extract Agent key
  L3: Verify sd_hash binding to L2, verify Agent signature

All layers use standard SD-JWT (RFC 9901) with typ='sd+jwt' and ES256.

Dependencies: jwcrypto
  pip install jwcrypto
"""

from __future__ import annotations

import json
from typing import Any

from jwcrypto import jwk, jws

from .sd_jwt_utils import (
    compute_sd_hash,
    parse_jwt_payload,
    verify_disclosures,
    verify_standard_claims,
)


# ==============================================================================
# Signature Verification
# ==============================================================================


def verify_signature(serialized: str, public_key: jwk.JWK) -> dict[str, Any]:
    """Verify an SD-JWT/JWT signature and return the payload.

    For L1 (no disclosures): verifies the JWT signature directly.
    For L2/L3 (with disclosures): verifies the issuer JWT signature.
    """
    jwt_part = serialized.split("~")[0]
    token = jws.JWS()
    token.deserialize(jwt_part)
    token.verify(public_key, alg="ES256")
    return json.loads(token.payload)


# ==============================================================================
# SD-Hash Binding Verification
# ==============================================================================


def verify_sd_hash_binding(current_serialized: str, prev_serialized: str) -> bool:
    """Verify that the sd_hash in current layer matches the hash of previous layer.

    L2.sd_hash must equal B64U(SHA-256(L1_serialized))
    L3.sd_hash must equal B64U(SHA-256(L2_serialized))
    """
    payload = parse_jwt_payload(current_serialized)
    expected_hash = compute_sd_hash(prev_serialized)
    actual_hash = payload.get("sd_hash", "")
    return actual_hash == expected_hash


# ==============================================================================
# Full Chain Verification
# ==============================================================================


def verify_credential_chain(
    l1_serialized: str,
    l2_serialized: str,
    alipayplus_public_key: jwk.JWK,
    *,
    expected_iss: str | None = None,
    expected_l2_aud: str | None = None,
    now: float | None = None,
    leeway: int = 60,
) -> dict[str, Any]:
    """Verify the base 2-layer credential chain (L1 + L2).

    Both IMMEDIATE and AUTONOMOUS modes require this verification.

    Verification logic:
    1. L1: Verify A+ signature, extract ISP public key from cnf.jwk
    2. L2: Verify sd_hash binding to L1, verify ISP signature, extract Agent key

    Standard JWT claims (exp/nbf/iat) are always enforced; audience/issuer are
    pinned only when ``expected_l2_aud``/``expected_iss`` are supplied by the caller.

    Returns: dict with {valid, l1_payload, l2_payload, errors}
    """
    errors: list[str] = []

    # --- L1 Verification ---
    try:
        l1_payload = verify_signature(l1_serialized, alipayplus_public_key)
    except Exception as exc:
        errors.append(f"L1 signature verification failed: {exc}")
        return {"valid": False, "errors": errors}

    # Verify L1 standard claims (exp/nbf/iat, and iss when pinned).
    try:
        verify_standard_claims(l1_payload, expected_iss=expected_iss, now=now, leeway=leeway)
    except Exception as exc:
        errors.append(f"L1 standard claims verification failed: {exc}")
        return {"valid": False, "errors": errors}

    # Extract ISP public key from L1.cnf.jwk
    try:
        cnf = l1_payload.get("cnf", {})
        isp_jwk_dict = cnf.get("jwk", {})
        isp_public_key = jwk.JWK(**isp_jwk_dict)
    except Exception as exc:
        errors.append(f"Failed to extract ISP public key from L1.cnf: {exc}")
        return {"valid": False, "errors": errors}

    # --- L2 Verification ---
    # Verify sd_hash binding: L2.sd_hash == B64U(SHA-256(L1))
    if not verify_sd_hash_binding(l2_serialized, l1_serialized):
        errors.append("L2 sd_hash does not match hash of L1")
        return {"valid": False, "errors": errors}

    # Verify L2 signature with ISP public key
    try:
        l2_payload = verify_signature(l2_serialized, isp_public_key)
    except Exception as exc:
        errors.append(f"L2 signature verification failed: {exc}")
        return {"valid": False, "errors": errors}

    # Verify L2 disclosures are bound to the signed _sd whitelist (RFC 9901).
    # Without this, the disclosure segment (checkout/intent/mandate_info) could
    # be tampered while the JWT signature still verifies.
    try:
        verify_disclosures(l2_serialized, l2_payload)
    except Exception as exc:
        errors.append(f"L2 disclosure binding verification failed: {exc}")
        return {"valid": False, "errors": errors}

    # Verify L2 standard claims (exp/nbf/iat, and aud when pinned).
    try:
        verify_standard_claims(l2_payload, expected_aud=expected_l2_aud, now=now, leeway=leeway)
    except Exception as exc:
        errors.append(f"L2 standard claims verification failed: {exc}")
        return {"valid": False, "errors": errors}

    return {
        "valid": True,
        "l1_payload": l1_payload,
        "l2_payload": l2_payload,
        "errors": [],
    }


def verify_agent_chain(
    l1_serialized: str,
    l2_serialized: str,
    l3_serialized: str,
    alipayplus_public_key: jwk.JWK,
    *,
    expected_iss: str | None = None,
    expected_l2_aud: str | None = None,
    expected_l3_aud: str | None = None,
    now: float | None = None,
    leeway: int = 60,
) -> dict[str, Any]:
    """Verify the full 3-layer agent authorization chain (L1 + L2 + L3).

    Required only in AUTONOMOUS mode (human-not-present), where the Agent
    independently authorizes the payment on behalf of the user.

    Verification logic:
    1. L1 + L2: Verify base credential chain (via verify_credential_chain)
    2. L3: Extract Agent public key from L2.cnf.jwk, verify sd_hash + signature

    Standard JWT claims (exp/nbf/iat) are always enforced; audience/issuer are
    pinned only when the ``expected_*`` values are supplied by the caller.

    Returns: dict with {valid, l1_payload, l2_payload, l3_payload, errors}
    """
    errors: list[str] = []

    # --- L1 + L2 Verification (reuse base credential chain logic) ---
    result = verify_credential_chain(
        l1_serialized,
        l2_serialized,
        alipayplus_public_key,
        expected_iss=expected_iss,
        expected_l2_aud=expected_l2_aud,
        now=now,
        leeway=leeway,
    )
    if not result["valid"]:
        return result

    l1_payload = result["l1_payload"]
    l2_payload = result["l2_payload"]

    # Extract Agent public key from L2.cnf.jwk
    try:
        cnf = l2_payload.get("cnf", {})
        agent_jwk_dict = cnf.get("jwk", {})
        agent_public_key = jwk.JWK(**agent_jwk_dict)
    except Exception as exc:
        errors.append(f"Failed to extract Agent public key from L2.cnf: {exc}")
        return {"valid": False, "errors": errors}

    # --- L3 Verification ---
    # Verify sd_hash binding: L3.sd_hash == B64U(SHA-256(L2))
    if not verify_sd_hash_binding(l3_serialized, l2_serialized):
        errors.append("L3 sd_hash does not match hash of L2")
        return {"valid": False, "errors": errors}

    # Verify L3 signature with Agent public key
    try:
        l3_payload = verify_signature(l3_serialized, agent_public_key)
    except Exception as exc:
        errors.append(f"L3 signature verification failed: {exc}")
        return {"valid": False, "errors": errors}

    # Verify L3 disclosures are bound to the signed _sd whitelist (RFC 9901).
    try:
        verify_disclosures(l3_serialized, l3_payload)
    except Exception as exc:
        errors.append(f"L3 disclosure binding verification failed: {exc}")
        return {"valid": False, "errors": errors}

    # Verify L3 standard claims (exp/nbf/iat, and aud when pinned).
    try:
        verify_standard_claims(l3_payload, expected_aud=expected_l3_aud, now=now, leeway=leeway)
    except Exception as exc:
        errors.append(f"L3 standard claims verification failed: {exc}")
        return {"valid": False, "errors": errors}

    return {
        "valid": True,
        "l1_payload": l1_payload,
        "l2_payload": l2_payload,
        "l3_payload": l3_payload,
        "errors": [],
    }
