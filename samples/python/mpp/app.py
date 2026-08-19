"""MPP FastAPI application."""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI

try:
    from .config import ALIPAYPLUS_BASE_URL, ResultCode
    from .models import (
        CreateAuthorizationBody,
        InquiryAuthorizationBody,
        PayBody,
        CompleteIdvBody,
    )
    from .store import MppStore
    from .alipayplus_client import AlipayPlusClient
    from .handlers import (
        handle_create_authorization,
        handle_inquiry_authorization,
        handle_pay,
        handle_complete_idv,
    )
except ImportError:
    from config import ALIPAYPLUS_BASE_URL, ResultCode
    from models import (
        CreateAuthorizationBody,
        InquiryAuthorizationBody,
        PayBody,
        CompleteIdvBody,
    )
    from store import MppStore
    from alipayplus_client import AlipayPlusClient
    from handlers import (
        handle_create_authorization,
        handle_inquiry_authorization,
        handle_pay,
        handle_complete_idv,
    )

# ``secret`` is a top-level samples/python module (same import either way);
# handlers, imported above, has already put samples/python on sys.path.
from secret import get_mpp_kid
from common.log_config import setup_logging

setup_logging("mpp")

app = FastAPI(
    title="MPP (Mobile Payment Platform) API",
    description="Open-source reference implementation of the Alipay+ MPP wallet service.",
    version="1.0.0",
)

from common.middleware import HttpLoggingMiddleware
app.add_middleware(HttpLoggingMiddleware, logger_name="mpp.http")

# Module-level singletons
store = MppStore()
client = AlipayPlusClient(base_url=ALIPAYPLUS_BASE_URL)


def _fail(code: str, message: str) -> dict:
    return {"result": {"resultCode": code, "resultStatus": "F", "resultMessage": message}}


@app.post("/createAuthorization")
def create_authorization(body: CreateAuthorizationBody) -> dict:
    """AlipayPlus → MPP: initiate IDV session for ENROLLMENT or MANDATE."""
    try:
        if not body.authSessionId:
            return _fail(ResultCode.PARAM_ILLEGAL, "authSessionId is required")
        if not body.authContext:
            return _fail(ResultCode.PARAM_ILLEGAL, "authContext is required")
        return handle_create_authorization(body, store, client)
    except Exception as exc:
        logging.getLogger("mpp.server").exception("[mpp/createAuthorization] unexpected error")
        return _fail(ResultCode.PARAM_ILLEGAL, str(exc))


@app.post("/inquiryAuthorization")
def inquiry_authorization(body: InquiryAuthorizationBody) -> dict:
    """AlipayPlus → MPP: poll IDV session status."""
    try:
        if not body.authSessionId:
            return _fail(ResultCode.PARAM_ILLEGAL, "authSessionId is required")
        if not body.authId:
            return _fail(ResultCode.PARAM_ILLEGAL, "authId is required")
        return handle_inquiry_authorization(body, store)
    except Exception as exc:
        logging.getLogger("mpp.server").exception("[mpp/inquiryAuthorization] unexpected error")
        return _fail(ResultCode.PARAM_ILLEGAL, str(exc))



@app.post("/pay")
def pay(body: PayBody) -> dict:
    """Acquirer/AlipayPlus → MPP: deTokenize payment token and settle."""
    try:
        if not body.paymentToken:
            return _fail(ResultCode.PARAM_ILLEGAL, "paymentToken is required")
        return handle_pay(body, store)
    except Exception as exc:
        logging.getLogger("mpp.server").exception("[mpp/pay] unexpected error")
        return _fail(ResultCode.PARAM_ILLEGAL, str(exc))


@app.post("/completeIdv")
def complete_idv(body: CompleteIdvBody) -> dict:
    """External trigger: simulates User completing biometric IDV at MPP.

    Called by the web demo backend when the user clicks 'Confirm' on the IDV card.
    Blocks for 5s (simulated biometric), then triggers MPP → ATS → CP notification chain.
    """
    try:
        if not body.authSessionId:
            return _fail(ResultCode.PARAM_ILLEGAL, "authSessionId is required")
        return handle_complete_idv(body.authSessionId, store, client)
    except Exception as exc:
        logging.getLogger("mpp.server").exception("[mpp/completeIdv] unexpected error")
        return _fail(ResultCode.PARAM_ILLEGAL, str(exc))


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "mpp"}


@app.get("/state")
def state() -> dict:
    return {"sessions": store.snapshot_sessions(), "ispKid": get_mpp_kid()}


@app.post("/reset")
def reset() -> dict:
    store.reset()
    return {"success": True}


if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI as _FastAPI
    from common.log_config import uvicorn_log_config

    _root = _FastAPI()
    _root.mount("/mpp", app)
    uvicorn.run(_root, host="0.0.0.0", port=int(os.environ.get("MPP_PORT", "8899")), log_level="warning", log_config=uvicorn_log_config())
