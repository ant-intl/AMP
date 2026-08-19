"""Pydantic request/response models for MPP service."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

import sys, pathlib
_project_root = pathlib.Path(__file__).resolve().parents[3]
_src_python = str(_project_root / "src" / "python")
if _src_python not in sys.path:
    sys.path.insert(0, _src_python)
from common.multi_currency_money import MultiCurrencyMoney


class IntentIn(BaseModel):
    raw: str = ""
    desc: str = ""
    expireTime: Optional[str] = None
    constraints: Optional[dict] = None


class CheckoutIn(BaseModel):
    totalAmount: Optional[MultiCurrencyMoney] = None
    merchant: Optional[dict] = None
    goods: Optional[list] = None


class CreateAuthorizationBody(BaseModel):
    authSessionId: str
    agentId: str
    customerId: str = ""
    authContext: list[str]
    intent: Optional[IntentIn] = None
    checkout: Optional[CheckoutIn] = None
    l1Serialized: Optional[str] = None


class InquiryAuthorizationBody(BaseModel):
    authSessionId: str
    authId: str


class PayBody(BaseModel):
    paymentToken: str
    amount: Optional[MultiCurrencyMoney] = None
    currency: str = "USD"


class CompleteIdvBody(BaseModel):
    """External trigger: simulates User completing biometric IDV at MPP."""
    authSessionId: str
