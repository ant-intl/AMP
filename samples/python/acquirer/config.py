"""Acquirer configuration constants."""

from __future__ import annotations

import os

# -------------------------------------------------------------------------
# CGCP (Contactless Gateway Code Protocol) payment token routing constants
#
# CGCP Header (8 chars):
#   Fixed Prefix    : "28"   (2 chars) — protocol identifier
#   Protocol Version: "1"    (1 char)  — version 1
#   Institution Code: "666"  (3 chars) — Alipay+ institution code
#   Business Type   : "23"   (2 chars) — mandate authorization token
#
# Payload (>= 16 chars): unique identifier for the payment token
# -------------------------------------------------------------------------
CGCP_FIXED_PREFIX = "28"
CGCP_PROTOCOL_VERSION = "1"
CGCP_INSTITUTION_CODE_ALIPAY_PLUS = "666"
CGCP_BUSINESS_TYPE_PAYMENT_TOKEN = "23"
CGCP_APLUS_PREFIX = "28166623"   # Full header = Fixed Prefix + Protocol Version + Institution Code + Business Type

# A+ network service URL (real HTTP service)
_alipayplus_network_port = os.environ.get("ALIPAYPLUS_NETWORK_PORT", "8083")
ALIPAYPLUS_NETWORK_BASE_URL: str = os.environ.get("ALIPAYPLUS_NETWORK_BASE_URL", f"http://localhost:{_alipayplus_network_port}")


class ResultCode:
    SUCCESS = "SUCCESS"
    UNKNOWN_NETWORK = "UNKNOWN_NETWORK"
    INVALID_PARAM = "INVALID_PARAM"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Merchant registry (for demo purposes)
# In production, this would be a database lookup
MERCHANT_REGISTRY = {
    "MERCHANT-DEMO-001": {
        "reference_merchant_id": "MERCHANT-DEMO-001",
        "merchant_mcc": "5411",
        "merchant_name": "UGG Demo Store",
        "merchant_display_name": "UGG",
        "merchant_address": {
            "region": "SG",
            "city": "Singapore",
        },
    },
}

# Default merchant info (fallback when merchant_id not found in registry)
DEFAULT_MERCHANT_INFO = {
    "reference_merchant_id": "UNKNOWN",
    "merchant_mcc": "0000",
    "merchant_name": "Unknown Merchant",
    "merchant_display_name": "Unknown",
    "merchant_address": {
        "region": "XX",
        "city": "Unknown",
    },
}
