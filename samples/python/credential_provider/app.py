"""Credential Provider FastAPI application factory.

CP Shopping-Agent-facing endpoints are registered under the
/credential-provider prefix (similar to /network, /mpp role paths).
AlipayPlus (network.py) and MPP run as separate processes; CP talks to
AlipayPlus via HTTP (client.py) and receives authorization results via
the /credential-provider/notifyAuthorization callback (plus legacy alias
paths used by the current AlipayPlus implementation).
"""

import pathlib
import sys

# Ensure project paths are available for imports
_project_root = pathlib.Path(__file__).resolve().parents[3]
_src_python = str(_project_root / "src" / "python")
_this_dir = str(pathlib.Path(__file__).resolve().parent)
for _p in (_src_python, _this_dir):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def build_app():
    """Build the FastAPI application with all CP endpoints."""
    from typing import Optional

    from fastapi import Body, FastAPI

    from service import (
        add_payment_method as _svc_add_pm,
        query_payment_method_list as _svc_query_pm,
        create_mandate_session as _svc_create_mandate,
        inquiry_mandate_session as _svc_inquiry_mandate,
        apply_credential as _svc_apply_cred,
        notify_authorization as _svc_notify_auth,
    )
    from models import (
        AddPaymentMethodRequest,
        AddPaymentMethodResponse,
        QueryPaymentMethodListRequest,
        QueryPaymentMethodListResponse,
        CreateMandateSessionRequest,
        CreateMandateSessionResponse,
        InquiryMandateSessionRequest,
        InquiryMandateSessionResponse,
        ApplyCredentialRequest,
        ApplyCredentialResponse,
        NotifyAuthorizationRequest,
        NotifyAuthorizationResponse,
    )

    app = FastAPI(
        title="Credential Provider Service",
        description="CP integrator bridging shopping-agent and AlipayPlus.",
        version="1.0.0",
    )

    from common.middleware import HttpLoggingMiddleware
    app.add_middleware(HttpLoggingMiddleware, logger_name="cp.http")

    # NOTE: All handlers are sync `def` (NOT async) so FastAPI runs them in a
    # threadpool. The initiate endpoints block waiting for the AlipayPlus
    # callback, which arrives on a separate request thread.

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": "credential-provider"}

    # -- Shopping-Agent-facing endpoints (role path: /credential-provider) --

    @app.post("/credential-provider/addPaymentMethod")
    def add_payment_method(body: AddPaymentMethodRequest = Body(AddPaymentMethodRequest())) -> AddPaymentMethodResponse:
        return _svc_add_pm(body)

    @app.post("/credential-provider/queryPaymentMethodList")
    def query_payment_method_list(body: Optional[QueryPaymentMethodListRequest] = Body(None)) -> QueryPaymentMethodListResponse:
        return _svc_query_pm(body)

    @app.post("/credential-provider/createMandateSession")
    def create_mandate_session(body: CreateMandateSessionRequest = Body(...)) -> CreateMandateSessionResponse:
        return _svc_create_mandate(body)

    @app.post("/credential-provider/inquiryMandateSession")
    def inquiry_mandate_session(body: InquiryMandateSessionRequest = Body(...)) -> InquiryMandateSessionResponse:
        return _svc_inquiry_mandate(body)

    @app.post("/credential-provider/applyCredential")
    def apply_credential(body: ApplyCredentialRequest = Body(...)) -> ApplyCredentialResponse:
        return _svc_apply_cred(body)

    # -- AlipayPlus-facing callback endpoint (role path: /credential-provider) --

    @app.post("/credential-provider/notifyAuthorization")
    def notify_authorization(body: NotifyAuthorizationRequest = Body(...)) -> NotifyAuthorizationResponse:
        return _svc_notify_auth(body)

    return app
