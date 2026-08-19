"""AlipayPlus Mandate HTTP API — thin adapter layer.

This module provides FastAPI endpoints that accept camelCase JSON, convert to
domain-level input objects, delegate to ``MandateService`` (pure domain logic
in ``mandate_chain.mandate``), and return the result dict.

File structure:
    1. Pydantic input models (HTTP-level)
    2. FastAPI app + endpoints
    3. Service instance
"""

from __future__ import annotations

import logging
import os
import pathlib
import sys
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Ensure the project src/python/ is on sys.path for ``schemas`` imports.
# ---------------------------------------------------------------------------
_project_root = pathlib.Path(__file__).resolve().parents[3]
_src_python = str(_project_root / "src" / "python")
if _src_python not in sys.path:
    sys.path.insert(0, _src_python)

from fastapi import FastAPI
from pydantic import BaseModel, Field

from mandate_chain.mandate import MandateService
from common.multi_currency_money import MultiCurrencyMoney

logger = logging.getLogger("mandate.server")


# ===================================================================
# 1. Pydantic input models (HTTP-level, camelCase tolerant)
# ===================================================================

class ConstraintsInput(BaseModel):
    """Constraints input."""
    merchantNameList: list[str] = Field(default_factory=list)
    merchantMccList: list[str] = Field(default_factory=list)


class CreateMandateInput(BaseModel):
    """Request body for creating a mandate record."""
    mandateId: str
    token: str = ""
    mandateType: str = ""
    description: str = ""
    raw: str = ""
    budgetAmount: Optional[MultiCurrencyMoney] = None
    constraints: Optional[ConstraintsInput] = None
    checkoutHash: Optional[str] = None
    expiryTime: str = ""
    extendInfo: Optional[dict[str, str]] = None
    tspSessionId: str = ""


class DeductAmountInput(BaseModel):
    """Request body for deducting mandate amount."""
    mandateId: str
    bizSerialNo: str
    cartAmount: MultiCurrencyMoney


class AdvanceStatusInput(BaseModel):
    """Request body for advancing mandate status."""
    mandateId: str


class ValidateForApplyCredentialInput(BaseModel):
    """Request body for validate."""
    mandateId: str
    mandateType: str = ""  # IMMEDIATE or AUTONOMOUS
    checkout: Optional[dict[str, Any]] = None  # camelCase checkout from CP


# ===================================================================
# 2. FastAPI app + endpoints
# ===================================================================

app = FastAPI(
    title="AlipayPlus Mandate Domain API",
    description="Pure domain service for mandate lifecycle management.",
    version="2.0.0",
)

from common.middleware import HttpLoggingMiddleware
app.add_middleware(HttpLoggingMiddleware, logger_name="mandate.http")


# -- Domain-level endpoints (called by network.py) --

@app.post("/mandate/create")
def mandate_create(body: CreateMandateInput) -> dict:
    """Create a mandate record with domain-level fields."""
    create_body = MandateService._CreateMandateBody(
        mandate_id=body.mandateId,
        tsp_session_id=body.tspSessionId,
        token=body.token,
        mandate_type=body.mandateType,
        description=body.description,
        raw=body.raw,
        expiry_time=body.expiryTime,
        checkout_hash=body.checkoutHash,
        extend_info=body.extendInfo,
    )
    if body.budgetAmount:
        create_body.budget_amount = body.budgetAmount
    if body.constraints:
        create_body.constraints = MandateService._ConstraintsIn(
            merchant_name_list=list(body.constraints.merchantNameList),
            merchant_mcc_list=list(body.constraints.merchantMccList),
        )
    return _svc.create_mandate(create_body)


@app.post("/mandate/deduct-amount")
def mandate_deduct(body: DeductAmountInput) -> dict:
    """Deduct amount from mandate budget."""
    return _svc.deduct_mandate_amount(MandateService._DeductAmountBody(
        mandate_id=body.mandateId,
        biz_serial_no=body.bizSerialNo,
        cart_amount=body.cartAmount,
    ))


@app.post("/mandate/advance-status")
def mandate_advance_status(body: AdvanceStatusInput) -> dict:
    """Advance mandate status (ACTIVE -> CLOSED when budget exhausted)."""
    return _svc.advance_mandate_status(MandateService._AdvanceStatusBody(
        mandate_id=body.mandateId,
    ))


@app.post("/mandate/validate")
def mandate_validate_for_apply(body: ValidateForApplyCredentialInput) -> dict:
    """Validate mandate intent before deduction.

    Checks:
      1. Mandate existence, status (ACTIVE), and expiry
      2. IMMEDIATE: checkout hash comparison
      3. AUTONOMOUS: merchant constraints validation
    """
    return _svc.validate(
        mandate_id=body.mandateId,
        mandate_type=body.mandateType,
        checkout=body.checkout,
    )


# ===================================================================
# 3. Service instance
# ===================================================================

_svc = MandateService()


if __name__ == "__main__":
    import uvicorn
    from common.log_config import uvicorn_log_config
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("ALIPAYPLUS_MANDATE_PORT", "8000")), log_level="warning", log_config=uvicorn_log_config())
