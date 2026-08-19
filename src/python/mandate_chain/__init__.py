"""AMP Verifiable Authorization Chain — SD-JWT credential chain (L1 -> L2 -> L3).

Re-exports core signing/verification utilities, generators and validators::

    from mandate_chain import generate_key_pair, public_jwk_dict
    from mandate_chain import create_alipayplus_layer1, create_immediate_layer2
    from mandate_chain import verify_credential_chain, verify_agent_chain
"""

from .sd_jwt_utils import (
    b64url_decode,
    b64url_encode,
    compute_sd_hash,
    create_jwt,
    generate_key_pair,
    hash_disclosure,
    parse_jwt_header,
    parse_jwt_payload,
    parse_sd_jwt_disclosures,
    public_jwk_dict,
    verify_disclosures,
    verify_standard_claims,
)
from .generator import (
    create_alipayplus_layer1,
    create_autonomous_layer2,
    create_checkout_layer3,
    create_immediate_layer2,
    create_layer1,
    create_layer2,
    create_layer3,
)
from .validator import (
    verify_agent_chain,
    verify_credential_chain,
    verify_sd_hash_binding,
    verify_signature,
)
from .mandate import (
    MandateService,
    MandateServiceException,
    ResultCode as MandateResultCode,
)

__all__ = [
    # SD-JWT utils
    "b64url_decode",
    "b64url_encode",
    "compute_sd_hash",
    "create_jwt",
    "generate_key_pair",
    "hash_disclosure",
    "parse_jwt_header",
    "parse_jwt_payload",
    "parse_sd_jwt_disclosures",
    "public_jwk_dict",
    "verify_disclosures",
    "verify_standard_claims",
    # Generators
    "create_alipayplus_layer1",
    "create_autonomous_layer2",
    "create_checkout_layer3",
    "create_immediate_layer2",
    "create_layer1",
    "create_layer2",
    "create_layer3",
    # Validators
    "verify_agent_chain",
    "verify_credential_chain",
    "verify_sd_hash_binding",
    "verify_signature",
    # Mandate domain service
    "MandateService",
    "MandateServiceException",
    "MandateResultCode",
]
