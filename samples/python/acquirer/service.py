"""Acquirer — minimal mock HTTP service.

Simulates payment processing. Real implementation owned by another team.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel


acquirer_router = APIRouter(prefix="/acquirer", tags=["acquirer"])


class PayBody(BaseModel):
    paymentToken: str
    checkout: Optional[dict[str, Any]] = None


@acquirer_router.post("/pay")
def pay(body: PayBody) -> dict:
    """Process payment (mock — always succeeds)."""
    return {"success": True, "data": {
        "transactionId": f"txn-{uuid.uuid4().hex[:8]}",
        "status": "SUCCESS",
        "paymentToken": body.paymentToken,
    }}
