"""MPP configuration constants."""

from __future__ import annotations

import os

_alipayplus_network_port = os.environ.get("ALIPAYPLUS_NETWORK_PORT", "8083")
ALIPAYPLUS_BASE_URL: str = os.environ.get("ALIPAYPLUS_BASE_URL", f"http://localhost:{_alipayplus_network_port}")

MPP_PSP_ID: str = "ALIPAY_HK"
MPP_WALLET_NAME: str = "AlipayHK"

AUTH_IN_PROCESS = "AUTH_IN_PROCESS"
AUTH_SUCCESS = "SUCCESS"
AUTH_FAILED = "FAILED"


class ResultCode:
    SUCCESS = "SUCCESS"
    PARAM_ILLEGAL = "PARAM_ILLEGAL"
    MPP_AUTH_FAILED = "MPP_AUTH_FAILED"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SYSTEM_ERROR = "SYSTEM_ERROR"
