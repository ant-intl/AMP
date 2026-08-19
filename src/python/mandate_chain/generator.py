from __future__ import annotations
"""AMP Mandate Chain - Generator.

Generates three-layer SD-JWT authorization chain:
  L1: Issued by A+ (Alipayplus), proves ISP identity is legitimate
  L2: Issued by ISP, confirms user identity verification and purchase intent
  L3: Issued by Agent, proves purchase decision within authorized scope

All layers use standard SD-JWT (RFC 9901) with typ='sd+jwt' and ES256.

Dependencies: jwcrypto, sd-jwt
  pip install jwcrypto sd-jwt
"""

import os
import time
from typing import Any

from jwcrypto import jwk
from sd_jwt.common import SDObj
from sd_jwt.issuer import SDJWTIssuer

from .sd_jwt_utils import (
    b64url_encode,
    compute_sd_hash,
    create_jwt,
    public_jwk_dict,
)


# ==============================================================================
# Layer Primitives
# ==============================================================================


def create_layer1(
    payload_claims: dict[str, Any],
    private_key: jwk.JWK,
    kid: str,
) -> str:
    """Create Layer 1 SD-JWT (no selective disclosures).

    L1 uses typ='sd+jwt' but has NO _sd or _sd_alg (MUST NOT per spec).
    Returns serialized SD-JWT format: <jwt>~
    """
    header = {
        "alg": "ES256",
        "typ": "sd+jwt",
        "kid": kid,
    }
    jwt_token = create_jwt(header, payload_claims, private_key)
    # SD-JWT format with zero disclosures: <jwt>~
    return jwt_token + "~"


def create_layer2(
    payload_claims: dict[str, Any],
    sd_claims: dict[str, Any],
    private_key: jwk.JWK,
    kid: str,
) -> str:
    """Create Layer 2 SD-JWT with selective disclosures.

    Args:
        payload_claims: Always-visible claims (nonce, aud, iat, exp, sd_hash, etc.)
        sd_claims: Selectively disclosable claims (intent, token_info, mandate_info)
        private_key: ISP's signing key
        kid: Key ID (must match L1.cnf.jwk.kid)

    Returns: Serialized SD-JWT: <jwt>~<disc1>~<disc2>~...~
    """
    # Merge visible and SD claims
    # dict[Any, Any] because sd_jwt uses SDObj(key) as a marker for selective disclosure
    claims: dict[Any, Any] = dict(payload_claims)
    for key, value in sd_claims.items():
        claims[SDObj(key)] = value

    header_params = {"typ": "sd+jwt", "kid": kid}

    issuer = SDJWTIssuer(
        user_claims=claims,
        issuer_key=private_key,
        holder_key=None,
        sign_alg=None,
        add_decoy_claims=False,
        serialization_format="compact",
        extra_header_parameters=header_params,
    )
    return issuer.sd_jwt_issuance


def create_layer3(
    payload_claims: dict[str, Any],
    sd_claims: dict[str, Any],
    private_key: jwk.JWK,
    kid: str,
) -> str:
    """Create Layer 3 SD-JWT with selective disclosures.

    Args:
        payload_claims: Always-visible claims (nonce, aud, iat, exp, sd_hash)
        sd_claims: Selectively disclosable claims (checkout)
        private_key: Agent's signing key
        kid: Key ID (must match L2.cnf.jwk.kid)

    Returns: Serialized SD-JWT: <jwt>~<disc1>~<disc2>~...~
    """
    return create_layer2(payload_claims, sd_claims, private_key, kid)


# ==============================================================================
# A+ Specific Generator Functions
# ==============================================================================


def create_alipayplus_layer1(
    sub: str,
    isp_public_key: jwk.JWK,
    isp_type: str,
    isp_name: str,
    private_key: jwk.JWK,
    kid: str,
    iss: str = "alipayplus.com",
    exp_seconds: int = 365 * 24 * 3600,
) -> str:
    """Create A+ Layer 1: proves ISP identity is legitimate.

    Signed by A+ private key. Binds ISP's public key via cnf.jwk.

    Args:
        sub: User identifier
        isp_public_key: ISP's public key (bound via cnf.jwk)
        isp_type: ISP type, e.g., "MPP"
        isp_name: ISP name, e.g., "ALIPAY_HK"
        private_key: A+ signing private key
        kid: A+ key ID
        iss: Issuer URI (default: alipayplus.com)
        exp_seconds: Expiration duration in seconds (default: 1 year)

    Returns: Serialized SD-JWT (L1)
    """
    now = int(time.time())
    payload: dict[str, Any] = {
        "iss": iss,
        "sub": sub,
        "iat": now,
        "exp": now + exp_seconds,
        "cnf": {"jwk": public_jwk_dict(isp_public_key)},
        "isp_type": isp_type,
        "isp_name": isp_name,
    }
    return create_layer1(payload, private_key, kid)


def create_immediate_layer2(
    l1_serialized: str,
    idv_result: str,
    idv_time: str,
    intent: dict[str, Any],
    token_info: dict[str, Any],
    mandate_info: dict[str, Any],
    checkout: dict[str, Any],
    private_key: jwk.JWK,
    kid: str,
    aud: str,
    nonce: str | None = None,
    exp_seconds: int = 10 * 60,
) -> str:
    """Create L2 for human-present (IMMEDIATE) mode.

    ISP confirms user identity verification and includes final checkout.
    No agent delegation (no cnf), no intent constraints.

    Args:
        l1_serialized: Serialized L1 SD-JWT (for sd_hash binding)
        idv_result: Identity verification result (e.g., "true")
        idv_time: Verification time (ISO 8601)
        intent: Intent object {raw, desc} (no expiry_time/constraints)
        token_info: Token info {token_unique_reference, token_status, ...}
        mandate_info: Mandate info {mandate_id, mandate_type, ...}
        checkout: Checkout object {total_amount, merchant, goods, ...}
        private_key: ISP's signing private key
        kid: ISP key ID (must match L1.cnf.jwk.kid)
        aud: Verifier identifier
        nonce: Anti-replay nonce (auto-generated if None)
        exp_seconds: Expiration in seconds (default: 10 minutes)

    Returns: Serialized SD-JWT (L2)
    """
    now = int(time.time())
    if nonce is None:
        nonce = b64url_encode(os.urandom(16))

    sd_hash = compute_sd_hash(l1_serialized)

    payload_claims = {
        "nonce": nonce,
        "aud": aud,
        "iat": now,
        "exp": now + exp_seconds,
        "sd_hash": sd_hash,
        "idv_result": idv_result,
        "idv_time": idv_time,
        "mode": "IMMEDIATE",
    }

    sd_claims = {
        "intent": intent,
        "token_info": token_info,
        "mandate_info": mandate_info,
        "checkout": checkout,
    }

    return create_layer2(payload_claims, sd_claims, private_key, kid)


def create_autonomous_layer2(
    l1_serialized: str,
    idv_result: str,
    idv_time: str,
    intent: dict[str, Any],
    token_info: dict[str, Any],
    mandate_info: dict[str, Any],
    agent_public_key: jwk.JWK,
    private_key: jwk.JWK,
    kid: str,
    aud: str,
    exp_seconds: int,
    nonce: str | None = None,
) -> str:
    """Create L2 for human-not-present (AUTONOMOUS) mode.

    ISP confirms user identity verification with intent constraints.
    Includes agent delegation via cnf.jwk for L3 binding.

    Args:
        l1_serialized: Serialized L1 SD-JWT (for sd_hash binding)
        idv_result: Identity verification result (e.g., "true")
        idv_time: Verification time (ISO 8601)
        intent: Intent object {raw, desc, expiry_time, constraints}
        token_info: Token info {token_unique_reference, token_status, ...}
        mandate_info: Mandate info {mandate_id, mandate_type, ...}
        agent_public_key: Agent's public key (bound via cnf.jwk for L3)
        private_key: ISP's signing private key
        kid: ISP key ID (must match L1.cnf.jwk.kid)
        aud: Verifier identifier
        exp_seconds: Expiration in seconds. REQUIRED, no default: an autonomous
            authorization must expire exactly when the user said it should, so
            the caller derives this from the user-specified expiry time.
        nonce: Anti-replay nonce (auto-generated if None)

    Returns: Serialized SD-JWT (L2)

    Raises:
        ValueError: exp_seconds is not a positive duration
    """
    if exp_seconds <= 0:
        raise ValueError(f"exp_seconds must be a positive duration, got {exp_seconds}")

    now = int(time.time())
    if nonce is None:
        nonce = b64url_encode(os.urandom(16))

    sd_hash = compute_sd_hash(l1_serialized)

    payload_claims = {
        "nonce": nonce,
        "aud": aud,
        "iat": now,
        "exp": now + exp_seconds,
        "sd_hash": sd_hash,
        "idv_result": idv_result,
        "idv_time": idv_time,
        "mode": "AUTONOMOUS",
        "cnf": {"jwk": public_jwk_dict(agent_public_key)},
    }

    sd_claims = {
        "intent": intent,
        "token_info": token_info,
        "mandate_info": mandate_info,
    }

    return create_layer2(payload_claims, sd_claims, private_key, kid)


def create_checkout_layer3(
    l2_serialized: str,
    checkout: dict[str, Any],
    private_key: jwk.JWK,
    kid: str,
    aud: str,
    nonce: str | None = None,
    exp_seconds: int = 10 * 60,
) -> str:
    """Create L3: Agent's purchase decision within authorized scope.

    Agent proves it made a valid checkout within user's intent constraints.
    L3.kid must match L2.cnf.jwk.kid.

    Args:
        l2_serialized: Serialized L2 SD-JWT (for sd_hash binding)
        checkout: Checkout object {total_amount, merchant, goods, ...}
        private_key: Agent's signing private key
        kid: Agent key ID (must match L2.cnf.jwk.kid)
        aud: Payment network URI
        nonce: Anti-replay nonce (auto-generated if None)
        exp_seconds: Expiration in seconds (default: 10 minutes)

    Returns: Serialized SD-JWT (L3)
    """
    now = int(time.time())
    if nonce is None:
        nonce = b64url_encode(os.urandom(16))

    sd_hash = compute_sd_hash(l2_serialized)

    payload_claims = {
        "nonce": nonce,
        "aud": aud,
        "iat": now,
        "exp": now + exp_seconds,
        "sd_hash": sd_hash,
    }

    sd_claims = {
        "checkout": checkout,
    }

    return create_layer3(payload_claims, sd_claims, private_key, kid)
