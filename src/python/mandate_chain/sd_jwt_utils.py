from __future__ import annotations
"""AMP Mandate Chain - SD-JWT utilities.

Provides the foundational SD-JWT operations shared by generator and validator:
  - Base64url encoding/decoding
  - SD-JWT hash computation (sd_hash)
  - ES256 (P-256) key pair generation and export
  - JWT/SD-JWT parsing helpers (header, payload, disclosures)
  - JWT creation (JWS compact serialization)

Module named `sd_jwt_utils` to avoid shadowing the PyJWT `jwt` package.

Dependencies: jwcrypto
  pip install jwcrypto
"""

import base64
import hashlib
import json
import time
from typing import Any

from jwcrypto import jwk, jws


# ==============================================================================
# Base64url Encoding / Decoding
# ==============================================================================


def b64url_encode(data: bytes) -> str:
    """Base64url encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(s: str) -> bytes:
    """Base64url decode with padding restoration."""
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


# ==============================================================================
# SD-JWT Hash
# ==============================================================================


def compute_sd_hash(serialized_token: str) -> str:
    """Compute sd_hash: B64U(SHA-256(ASCII(serialized_token)))."""
    digest = hashlib.sha256(serialized_token.encode("ascii")).digest()
    return b64url_encode(digest)


# ==============================================================================
# Key Management
# ==============================================================================


def generate_key_pair(kid: str | None = None) -> jwk.JWK:
    """Generate an ES256 (P-256) key pair with optional kid."""
    key = jwk.JWK.generate(kty="EC", crv="P-256")
    if kid:
        key["kid"] = kid
    return key


def public_jwk_dict(key: jwk.JWK) -> dict[str, Any]:
    """Export public JWK as dict (includes kid if set)."""
    return json.loads(key.export_public())


# ==============================================================================
# JWT / SD-JWT Parsing
# ==============================================================================


def parse_jwt_payload(token: str) -> dict[str, Any]:
    """Parse a JWT/SD-JWT and return the payload dict (without verification)."""
    jwt_part = token.split("~")[0] if "~" in token else token
    parts = jwt_part.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")
    payload_bytes = b64url_decode(parts[1])
    return json.loads(payload_bytes)


def parse_jwt_header(token: str) -> dict[str, Any]:
    """Parse a JWT/SD-JWT and return the header dict."""
    jwt_part = token.split("~")[0] if "~" in token else token
    parts = jwt_part.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")
    header_bytes = b64url_decode(parts[0])
    return json.loads(header_bytes)


def parse_sd_jwt_disclosures(serialized: str) -> list[dict[str, Any]]:
    """Parse SD-JWT disclosures and return decoded disclosure values."""
    parts = serialized.split("~")
    disclosures = [p for p in parts[1:] if p]
    results: list[dict[str, Any]] = []
    for disc in disclosures:
        try:
            decoded = json.loads(b64url_decode(disc))
            results.append(decoded)
        except Exception:
            continue
    return results


# ==============================================================================
# Selective Disclosure Binding (RFC 9901 _sd whitelist)
# ==============================================================================


def hash_disclosure(disclosure_str: str) -> str:
    """Compute the SD-JWT disclosure digest: B64U(SHA-256(ASCII(disclosure))).

    The digest is taken over the base64url-encoded disclosure STRING (not the
    decoded JSON), matching how issuers populate the signed ``_sd`` array.
    """
    digest = hashlib.sha256(disclosure_str.encode("ascii")).digest()
    return b64url_encode(digest)


def verify_disclosures(serialized: str, payload: dict[str, Any]) -> None:
    """Verify every disclosure is bound to the signed ``_sd`` whitelist.

    RFC 9901 requires each presented disclosure to hash to an entry inside the
    signature-protected ``_sd`` array. Without this check, the disclosure
    segment (which carries sensitive claims such as ``checkout``) could be
    freely added/removed/modified while the JWT signature still verifies.

    Raises:
        ValueError: if the algorithm is unsupported, a disclosure does not map
            to an ``_sd`` entry, or a disclosure hash is duplicated.
    """
    parts = serialized.split("~")
    disclosure_strs = [p for p in parts[1:] if p]

    # No disclosures (e.g. L1): nothing to bind, and _sd MUST be absent.
    if not disclosure_strs:
        return

    sd_alg = payload.get("_sd_alg", "sha-256")
    if sd_alg != "sha-256":
        raise ValueError(f"unsupported _sd_alg: {sd_alg!r}")

    sd_hashes = payload.get("_sd", [])
    if not isinstance(sd_hashes, list):
        raise ValueError("payload _sd is missing or not a list")
    sd_set = set(sd_hashes)

    seen: set[str] = set()
    for disc in disclosure_strs:
        digest = hash_disclosure(disc)
        if digest not in sd_set:
            raise ValueError("disclosure not bound to signed _sd whitelist")
        if digest in seen:
            raise ValueError("duplicate disclosure hash")
        seen.add(digest)


# ==============================================================================
# Standard Claims Validation (exp / nbf / iat / aud / iss)
# ==============================================================================


def verify_standard_claims(
    payload: dict[str, Any],
    *,
    expected_aud: str | None = None,
    expected_iss: str | None = None,
    now: float | None = None,
    leeway: int = 60,
) -> None:
    """Verify the JWT standard lifecycle/audience claims.

    SD-JWT tokens carry ``exp``/``iat`` (and optionally ``nbf``/``aud``/``iss``),
    but verifying only the signature and ``sd_hash`` chain leaves these
    unchecked, allowing expired tokens to be replayed and audience/issuer
    mismatches to go unnoticed.

    Rules:
      - ``exp``: if present, require ``now <= exp + leeway`` (else expired).
      - ``nbf``: if present, require ``now >= nbf - leeway`` (else not yet valid).
      - ``iat``: if present, require ``iat <= now + leeway`` (clock-skew sanity).
      - ``aud``: enforced only when ``expected_aud`` is supplied; accepts either a
        string or a list of audiences.
      - ``iss``: enforced only when ``expected_iss`` is supplied.

    ``leeway`` (seconds) absorbs benign clock skew between signer and verifier.

    Raises:
        ValueError: if any present claim fails its check.
    """
    current = time.time() if now is None else now

    exp = payload.get("exp")
    if exp is not None:
        if current > float(exp) + leeway:
            raise ValueError(f"token expired (exp={exp}, now={int(current)})")

    nbf = payload.get("nbf")
    if nbf is not None:
        if current < float(nbf) - leeway:
            raise ValueError(f"token not yet valid (nbf={nbf}, now={int(current)})")

    iat = payload.get("iat")
    if iat is not None:
        if float(iat) > current + leeway:
            raise ValueError(f"token issued in the future (iat={iat}, now={int(current)})")

    if expected_aud is not None:
        aud = payload.get("aud")
        aud_set = set(aud) if isinstance(aud, list) else {aud}
        if expected_aud not in aud_set:
            raise ValueError(f"audience mismatch (expected {expected_aud!r}, got {aud!r})")

    if expected_iss is not None:
        iss = payload.get("iss")
        if iss != expected_iss:
            raise ValueError(f"issuer mismatch (expected {expected_iss!r}, got {iss!r})")


# ==============================================================================
# JWT Creation (base utility)
# ==============================================================================


def create_jwt(header: dict[str, Any], payload: dict[str, Any], private_key: jwk.JWK) -> str:
    """Create a signed JWT (JWS compact serialization).

    Base utility for creating any signed JWT with ES256.
    Returns: base64url(header).base64url(payload).base64url(signature)
    """
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    token = jws.JWS(payload_bytes)
    protected_header = json.dumps(header, separators=(",", ":"))
    token.add_signature(private_key, alg="ES256", protected=protected_header)
    return token.serialize(compact=True)
