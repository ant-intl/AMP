"""Mandate domain service — pure business logic for mandate lifecycle management.

This module contains no HTTP / framework dependencies.  It is consumed by
``samples/python/alipayplus/mandate.py`` (thin FastAPI adapter) and can be
re-used by any other transport layer.

Structure:
    1. Constants (ResultCode, _CODE_NAME_MAP)
    2. MandateServiceException
    3. MandateService (domain logic)
    4. Private helper functions
    5. Checkout hash computation
"""

from __future__ import annotations

import base64
import hashlib
import json
import threading
from datetime import datetime, timezone
from typing import Any, Optional, TypeVar

from pydantic import BaseModel, Field

from schemas.mandate import (
    Budget,
    Mandate,
    MandateConstraints,
    MandateExtendType,
    MandateStatus,
    MandateType,
)
from common.multi_currency_money import MultiCurrencyMoney


# ===================================================================
# 1. Constants
# ===================================================================

class ResultCode:
    SUCCESS = "0000"
    PARAM_ILLEGAL = "1001"
    MANDATE_NOT_EXIST = "2001"
    MANDATE_STATUS_INVALID = "2002"
    MANDATE_EXPIRED = "2003"
    MANDATE_BALANCE_INSUFFICIENT = "2004"
    MANDATE_USED_AMOUNT_INSUFFICIENT = "2005"
    TOKEN_NOT_MATCH_MANDATE = "2006"
    CHECKOUT_HASH_INCONSISTENT = "2007"
    MERCHANT_NOT_IN_CONSTRAINTS = "2008"
    REPEAT_REQ_INCONSISTENT = "2009"
    CHECKOUT_AMOUNT_EXCEEDS_BUDGET = "2010"
    CHECKOUT_CURRENCY_MISMATCH = "2011"


_CODE_NAME_MAP: dict[str, str] = {
    ResultCode.SUCCESS: "SUCCESS",
    ResultCode.PARAM_ILLEGAL: "PARAM_ILLEGAL",
    ResultCode.MANDATE_NOT_EXIST: "MANDATE_NOT_EXIST",
    ResultCode.MANDATE_STATUS_INVALID: "MANDATE_STATUS_INVALID",
    ResultCode.MANDATE_EXPIRED: "MANDATE_EXPIRED",
    ResultCode.MANDATE_BALANCE_INSUFFICIENT: "MANDATE_BALANCE_INSUFFICIENT",
    ResultCode.MANDATE_USED_AMOUNT_INSUFFICIENT: "MANDATE_USED_AMOUNT_INSUFFICIENT",
    ResultCode.TOKEN_NOT_MATCH_MANDATE: "TOKEN_NOT_MATCH_MANDATE",
    ResultCode.CHECKOUT_HASH_INCONSISTENT: "CHECKOUT_HASH_INCONSISTENT",
    ResultCode.MERCHANT_NOT_IN_CONSTRAINTS: "MERCHANT_NOT_IN_CONSTRAINTS",
    ResultCode.REPEAT_REQ_INCONSISTENT: "REPEAT_REQ_INCONSISTENT",
    ResultCode.CHECKOUT_AMOUNT_EXCEEDS_BUDGET: "CHECKOUT_AMOUNT_EXCEEDS_BUDGET",
    ResultCode.CHECKOUT_CURRENCY_MISMATCH: "CHECKOUT_CURRENCY_MISMATCH",
}


# ===================================================================
# 2. Exception
# ===================================================================

class MandateServiceException(Exception):
    """Raised when a mandate business rule is violated."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.result_code = code
        self.result_message = message


# ===================================================================
# 3. MandateService
# ===================================================================

class MandateService:
    """Mandate core domain service — manages mandate lifecycle (create, deduct, status advance).

    Persistence dependencies are injected via constructor parameters:
        repo_factory: callable that returns a ``SqliteRepo``-compatible object
    """

    # ------------------------------------------------------------------
    # Internal models (MandateService internal use only)
    # ------------------------------------------------------------------

    class _ConstraintsIn(BaseModel):
        """Internal constraints — corresponds to MandateConstraints."""
        merchant_name_list: list[str] = Field(default_factory=list)
        merchant_mcc_list: list[str] = Field(default_factory=list)

    class _CreateMandateBody(BaseModel):
        mandate_id: str
        tsp_session_id: str = ""
        token: str = ""
        mandate_type: str = ""
        description: str = ""
        raw: str = ""
        budget_amount: Optional[MultiCurrencyMoney] = None
        constraints: Optional["MandateService._ConstraintsIn"] = None
        checkout_hash: Optional[str] = None
        expiry_time: str = ""
        extend_info: Optional[dict[str, str]] = None

    class _DeductAmountBody(BaseModel):
        mandate_id: str
        biz_serial_no: str
        cart_amount: MultiCurrencyMoney

    class _AdvanceStatusBody(BaseModel):
        mandate_id: str

    def __init__(self, repo_factory: Any = None) -> None:
        if repo_factory is not None:
            self._repo = repo_factory()
        else:
            # Default: lazy import to avoid hard-coding paths at module level
            from common.sqlite_store import SqliteRepo
            from alipayplus.stores import TOKEN_STORE_PATH, MandateModel
            self._repo = SqliteRepo(TOKEN_STORE_PATH, MandateModel)
        self._timers: dict[str, threading.Timer] = {}
        self._timer_lock = threading.Lock()

    # (1) create_mandate
    def create_mandate(self, body: MandateService._CreateMandateBody) -> dict:
        try:
            _not_blank(body.mandate_id, ResultCode.PARAM_ILLEGAL, "mandateId cannot be blank")
            if body.mandate_type == MandateType.AUTONOMOUS.value:
                _not_none(body.constraints, ResultCode.PARAM_ILLEGAL, "constraints cannot be null for AUTONOMOUS")
            else:
                _not_blank(body.checkout_hash, ResultCode.PARAM_ILLEGAL, "checkoutHash cannot be blank for IMMEDIATE")
            mandate = _build_mandate(body)
            mandate_model = _to_mandate_model(mandate)
            self._repo.save(mandate_model)
            self._schedule_expiry(mandate)
            return _ok({"mandateId": mandate.mandate_id})
        except MandateServiceException as e:
            return _fail(e.result_code, e.result_message)

    # (2) deduct_mandate_amount
    def deduct_mandate_amount(self, body: MandateService._DeductAmountBody) -> dict:
        cart = body.cart_amount
        try:
            self._repo.acquire()
            locked = self._repo.get_locked(body.mandate_id)
            try:
                locked = _not_none(locked, ResultCode.MANDATE_NOT_EXIST, f"mandate not found, mandateId={body.mandate_id}")
                # Reject non-positive deductions: a negative cart_amount would pass the
                # `remaining >= cart` balance check trivially and then INFLATE the budget
                # via `remaining.subtract(cart)` (remaining - negative = remaining + |cart|).
                _is_true(cart.fetch_minor_units() > 0, ResultCode.PARAM_ILLEGAL, f"deduct amount must be positive, mandateId={body.mandate_id}, cent={cart.fetch_minor_units()}")
                for entry in locked.fetch_ext_info_list(MandateExtendType.DEDUCTED):
                    parts = entry.split("|")
                    if parts[0] == body.biz_serial_no:
                        _is_true(parts[1] == cart.currency_code and parts[2] == cart.fetch_amount_str(), ResultCode.REPEAT_REQ_INCONSISTENT, f"deduct amount inconsistent, bizSerialNo={body.biz_serial_no}")
                        return _ok({"mandate": _mandate_to_dict(locked)})
                assert locked.budget is not None
                assert locked.budget.total_budget_amount is not None
                _is_true(locked.budget.total_budget_amount.currency_code == cart.currency_code, ResultCode.PARAM_ILLEGAL, f"currency mismatch, mandateId={body.mandate_id}")
                _is_true(locked.mandate_status == MandateStatus.ACTIVE, ResultCode.MANDATE_STATUS_INVALID, f"mandate status invalid, mandateId={body.mandate_id}")
                assert locked.budget.remaining_amount is not None
                _is_true(locked.budget.remaining_amount.compare_to(cart) >= 0, ResultCode.MANDATE_BALANCE_INSUFFICIENT, f"insufficient balance, mandateId={body.mandate_id}")
                assert locked.budget.used_amount is not None
                locked.budget.used_amount = locked.budget.used_amount.add(cart)
                locked.budget.remaining_amount = locked.budget.remaining_amount.subtract(cart)
                locked.gmt_modified = datetime.now(timezone.utc)
                locked.append_ext_info_list(MandateExtendType.DEDUCTED, f"{body.biz_serial_no}|{cart.currency_code}|{cart.fetch_amount_str()}")
                self._repo.save_locked(_to_mandate_model(locked))
                return _ok({"mandate": _mandate_to_dict(locked)})
            finally:
                self._repo.release()
        except MandateServiceException as e:
            self._repo.release()
            return _fail(e.result_code, e.result_message)

    # (3) advance_mandate_status
    def advance_mandate_status(self, body: MandateService._AdvanceStatusBody) -> dict:
        try:
            self._repo.acquire()
            locked = self._repo.get_locked(body.mandate_id)
            try:
                if locked is None or locked.mandate_status != MandateStatus.ACTIVE:
                    return _ok({"mandateStatus": locked.mandate_status.value if locked and locked.mandate_status else "UNKNOWN"})
                status = locked.mandate_status.value  # type: ignore[union-attr]
                if locked.budget and locked.budget.remaining_amount and locked.budget.remaining_amount.cent <= 0:
                    locked.mandate_status = MandateStatus.CLOSED
                    locked.closed_time = datetime.now(timezone.utc)
                    locked.gmt_modified = datetime.now(timezone.utc)
                    self._repo.save_locked(_to_mandate_model(locked))
                    status = MandateStatus.CLOSED.value
                return _ok({"mandateStatus": status})
            finally:
                self._repo.release()
        except MandateServiceException as e:
            self._repo.release()
            return _fail(e.result_code, e.result_message)

    # (4) validate
    def validate(
        self, *, mandate_id: str, mandate_type: str = "", checkout: dict[str, Any] | None = None,
    ) -> dict:
        """Unified mandate intent validation for applyCredential.

        Validates (in order):
            1. Mandate existence, status (ACTIVE), and expiry
            2. IMMEDIATE: checkout hash comparison
            3. AUTONOMOUS: merchant constraints validation (name + mcc)

        Returns full mandate info for downstream steps (deduct, token issue, etc.).
        """
        try:
            # Step 1: Validate mandate existence, status, and expiry
            mandate = self._validate_mandate_status_and_expiry(mandate_id)

            # Step 2: Resolve and validate checkout based on mandate type
            m_type = mandate_type or (mandate.mandate_type.value if mandate.mandate_type else "")
            self._resolve_and_validate_checkout(mandate, m_type, checkout)

            result = _mandate_to_dict(mandate)
            result["checkout"] = checkout
            return _ok(result)
        except MandateServiceException as exc:
            return _fail(exc.result_code, exc.result_message)
        except Exception as exc:
            return _fail(ResultCode.PARAM_ILLEGAL, str(exc))

    def _validate_mandate_status_and_expiry(self, mandate_id: str) -> Mandate:
        """Query mandate and verify status is ACTIVE and not expired."""
        mandate = _not_none(
            self._repo.get(mandate_id),
            ResultCode.MANDATE_NOT_EXIST,
            f"mandate not found, mandateId={mandate_id}",
        )
        _is_true(
            mandate.mandate_status == MandateStatus.ACTIVE,
            ResultCode.MANDATE_STATUS_INVALID,
            f"mandate status is not ACTIVE, mandateId={mandate_id}",
        )
        if mandate.expiry_time is not None:
            _is_true(
                datetime.now(timezone.utc) <= mandate.expiry_time,
                ResultCode.MANDATE_EXPIRED,
                f"mandate expired, mandateId={mandate_id}",
            )
        return mandate

    def _resolve_and_validate_checkout(
        self, mandate: Mandate, mandate_type: str, checkout: dict[str, Any] | None,
    ) -> None:
        """Resolve checkout and validate based on mandate type.

        IMMEDIATE: hash comparison + budget amount/currency must equal checkout amount
        AUTONOMOUS: checkout required, must satisfy merchant constraints + amount <= remaining
        """
        if mandate_type == MandateType.IMMEDIATE.value:
            # IMMEDIATE: checkout hash comparison
            if mandate.checkout_hash and checkout:
                chain_checkout = _to_chain_format(checkout)
                request_hash = _compute_checkout_hash(chain_checkout)
                _is_true(
                    mandate.checkout_hash == request_hash,
                    ResultCode.CHECKOUT_HASH_INCONSISTENT,
                    "checkout hash does not match mandate checkout_hash",
                )
            # IMMEDIATE: budget amount/currency must equal checkout totalAmount
            if checkout and mandate.budget and mandate.budget.total_budget_amount:
                self._validate_immediate_budget_amount(mandate, checkout)
        elif mandate_type == MandateType.AUTONOMOUS.value:
            # AUTONOMOUS: checkout required
            _not_none(checkout, ResultCode.PARAM_ILLEGAL, "checkout is required for AUTONOMOUS mandate")
            # Validate merchant constraints (checkout is guaranteed non-None after _not_none)
            self._validate_checkout_constraints(mandate, checkout)  # type: ignore[arg-type]
            # AUTONOMOUS: checkout amount must <= remaining budget
            if mandate.budget and mandate.budget.remaining_amount:
                self._validate_autonomous_budget_amount(mandate, checkout)  # type: ignore[arg-type]

    @staticmethod
    def _validate_immediate_budget_amount(mandate: Mandate, checkout: dict[str, Any]) -> None:
        """IMMEDIATE: budget total and remaining must equal checkout totalAmount."""
        ta = checkout.get("totalAmount", {})
        checkout_cent = ta.get("cent", 0)
        checkout_currency = ta.get("currency", "USD")

        assert mandate.budget is not None
        budget_total = mandate.budget.total_budget_amount
        budget_remaining = mandate.budget.remaining_amount

        # Currency must match
        if budget_total:
            _is_true(
                budget_total.currency_code == checkout_currency,
                ResultCode.CHECKOUT_CURRENCY_MISMATCH,
                f"currency mismatch: mandate={budget_total.currency_code}, checkout={checkout_currency}",
            )
            # Total budget must equal checkout amount
            _is_true(
                budget_total.cent == checkout_cent,
                ResultCode.CHECKOUT_AMOUNT_EXCEEDS_BUDGET,
                f"IMMEDIATE budget mismatch: total_budget={budget_total.cent} != checkout={checkout_cent}",
            )
        # Remaining must equal checkout amount (for first use)
        if budget_remaining:
            _is_true(
                budget_remaining.cent == checkout_cent,
                ResultCode.CHECKOUT_AMOUNT_EXCEEDS_BUDGET,
                f"IMMEDIATE budget mismatch: remaining={budget_remaining.cent} != checkout={checkout_cent}",
            )

    @staticmethod
    def _validate_autonomous_budget_amount(mandate: Mandate, checkout: dict[str, Any]) -> None:
        """AUTONOMOUS: checkout amount must <= remaining budget."""
        ta = checkout.get("totalAmount", {})
        checkout_cent = ta.get("cent", 0)
        checkout_currency = ta.get("currency", "USD")

        assert mandate.budget is not None
        budget_remaining = mandate.budget.remaining_amount
        if budget_remaining:
            # Currency must match
            _is_true(
                budget_remaining.currency_code == checkout_currency,
                ResultCode.CHECKOUT_CURRENCY_MISMATCH,
                f"currency mismatch: mandate={budget_remaining.currency_code}, checkout={checkout_currency}",
            )
            # Checkout amount must <= remaining
            _is_true(
                checkout_cent <= budget_remaining.cent,
                ResultCode.CHECKOUT_AMOUNT_EXCEEDS_BUDGET,
                f"AUTONOMOUS budget exceeded: checkout={checkout_cent} > remaining={budget_remaining.cent}",
            )

    @staticmethod
    def _validate_checkout_constraints(mandate: Mandate, checkout: dict[str, Any]) -> None:
        """Validate AUTONOMOUS checkout against mandate merchant constraints."""
        if not mandate.constraints:
            return
        c = mandate.constraints
        names = c.merchant_name_list or []
        mccs = c.merchant_mcc_list or []
        if not names and not mccs:
            return

        merchant = checkout.get("merchant", {})
        m_name = merchant.get("merchantName", "")
        m_mcc = merchant.get("merchantMcc", "")

        name_ok = (not names) or (m_name in names if m_name else False)
        mcc_ok = (not mccs) or (m_mcc in mccs if m_mcc else False)
        _is_true(
            name_ok and mcc_ok,
            ResultCode.MERCHANT_NOT_IN_CONSTRAINTS,
            f"merchant not in constraints: name={m_name}, mcc={m_mcc}",
        )

    # -- MandateService private methods --

    def _schedule_expiry(self, mandate: Mandate) -> None:
        if mandate.expiry_time is None:
            return
        delay = (mandate.expiry_time - datetime.now(timezone.utc)).total_seconds()
        if delay <= 0:
            return

        def _expire(mid: str) -> None:
            self._repo.acquire()
            locked = self._repo.get_locked(mid)
            try:
                if locked and locked.mandate_status == MandateStatus.ACTIVE:
                    locked.mandate_status = MandateStatus.EXPIRED
                    locked.gmt_modified = datetime.now(timezone.utc)
                    self._repo.save_locked(_to_mandate_model(locked))
            finally:
                self._repo.release()
            with self._timer_lock:
                self._timers.pop(mid, None)

        t = threading.Timer(delay, _expire, args=[mandate.mandate_id])
        t.daemon = True
        t.start()
        with self._timer_lock:
            self._timers[mandate.mandate_id or ""] = t


# ===================================================================
# 4. Private helper functions
# ===================================================================

_T = TypeVar("_T")


def _is_true(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise MandateServiceException(code, message)


def _not_none(value: _T | None, code: str, message: str) -> _T:
    if value is None:
        raise MandateServiceException(code, message)
    return value


def _not_blank(value: str | None, code: str, message: str) -> None:
    if not value or not value.strip():
        raise MandateServiceException(code, message)


def _ok(data: dict[str, Any] | None = None) -> dict[str, Any]:
    resp: dict[str, Any] = {"success": True, "resultCode": "SUCCESS", "resultMessage": "SUCCESS"}
    if data:
        resp["data"] = data
    return resp


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"success": False, "resultCode": _CODE_NAME_MAP.get(code, code), "resultMessage": message}


def _parse_dt(value: str) -> datetime:
    if not value:
        raise ValueError("empty")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    raise ValueError(f"Unable to parse datetime: {value}")


def _to_money(m: MultiCurrencyMoney) -> MultiCurrencyMoney:
    """Identity function — input is already MultiCurrencyMoney."""
    return m


def _to_mandate_model(m: Mandate) -> Any:
    """Convert a Mandate domain object to a MandateModel for persistence."""
    from alipayplus.stores import MandateModel
    model = MandateModel()
    for f in Mandate.__dataclass_fields__:
        setattr(model, f, getattr(m, f))
    return model


def _mandate_to_dict(mandate: Mandate) -> dict[str, Any]:
    """Serialize a Mandate domain object into a complete dict for HTTP responses."""
    budget_data = None
    if mandate.budget and mandate.budget.total_budget_amount:
        budget_data = {
            "totalBudgetAmount": {
                "cent": mandate.budget.total_budget_amount.cent,
                "currency": mandate.budget.total_budget_amount.currency_code,
                "value": mandate.budget.total_budget_amount.fetch_amount_str(),
            },
            "remainingAmount": {
                "cent": mandate.budget.remaining_amount.cent if mandate.budget.remaining_amount else 0,
                "currency": mandate.budget.remaining_amount.currency_code if mandate.budget.remaining_amount else "USD",
                "value": mandate.budget.remaining_amount.fetch_amount_str() if mandate.budget.remaining_amount else "0",
            },
            "usedAmount": {
                "cent": mandate.budget.used_amount.cent if mandate.budget.used_amount else 0,
                "currency": mandate.budget.used_amount.currency_code if mandate.budget.used_amount else "USD",
                "value": mandate.budget.used_amount.fetch_amount_str() if mandate.budget.used_amount else "0",
            },
        }
    constraints_data = None
    if mandate.constraints:
        constraints_data = {
            "merchantNameList": mandate.constraints.merchant_name_list or [],
            "merchantMccList": mandate.constraints.merchant_mcc_list or [],
        }
    return {
        "mandateId": mandate.mandate_id or "",
        "mandateType": mandate.mandate_type.value if mandate.mandate_type else "",
        "mandateStatus": mandate.mandate_status.value if mandate.mandate_status else "",
        "expiryTime": mandate.expiry_time.isoformat() if mandate.expiry_time else "",
        "checkoutHash": mandate.checkout_hash or "",
        "budget": budget_data,
        "constraints": constraints_data,
    }


def _build_mandate(body: MandateService._CreateMandateBody) -> Mandate:
    m = Mandate()
    m.mandate_id = body.mandate_id
    m.token = body.token
    m.mandate_type = MandateType(body.mandate_type) if body.mandate_type else None
    m.mandate_status = MandateStatus.ACTIVE
    m.description = body.description
    m.raw = body.raw
    m.expiry_time = _parse_dt(body.expiry_time)
    m.budget = Budget()
    if body.budget_amount:
        total = body.budget_amount
        m.budget.total_budget_amount = total
        m.budget.used_amount = MultiCurrencyMoney.of(0, total.currency_code)
        m.budget.remaining_amount = MultiCurrencyMoney.of(total.fetch_minor_units(), total.currency_code)
    if body.checkout_hash:
        m.checkout_hash = body.checkout_hash
    if body.constraints:
        m.constraints = MandateConstraints(
            merchant_name_list=list(body.constraints.merchant_name_list),
            merchant_mcc_list=list(body.constraints.merchant_mcc_list),
        )
    if body.extend_info:
        for k, v in body.extend_info.items():
            m.put_ext_info(MandateExtendType(k), v)  # type: ignore[arg-type]
    now = datetime.now(timezone.utc)
    m.gmt_create = now
    m.gmt_modified = now
    return m


# ===================================================================
# 5. Checkout hash computation
# ===================================================================

def _to_chain_format(checkout: dict[str, Any]) -> dict[str, Any]:
    """Convert checkout to snake_case chain format for hash computation.

    Handles both camelCase (from API request) and snake_case (from L2 disclosure/storage).
    Includes total_amount, merchant, and goods (matching L2 checkout disclosure format).
    """
    # Detect format: if total_amount exists, it's already snake_case
    if "total_amount" in checkout:
        # Already snake_case (from L2 disclosure or storage)
        ta = checkout.get("total_amount", {})
        merchant = checkout.get("merchant", {})
        result: dict[str, Any] = {
            "total_amount": {
                "currency": ta.get("currency", "USD"),
                "amount": ta.get("amount", ta.get("cent", 0)),
            },
            "merchant": {
                "reference_merchant_id": merchant.get("reference_merchant_id", merchant.get("merchantId", "")),
                "merchant_name": merchant.get("merchant_name", merchant.get("merchantName", "")),
                "merchant_mcc": merchant.get("merchant_mcc", merchant.get("merchantMcc", "")),
            },
        }
    else:
        # camelCase (from API request) - convert to snake_case
        ta = checkout.get("totalAmount", {})
        merchant = checkout.get("merchant", {})
        result = {
            "total_amount": {"currency": ta.get("currency", "USD"), "amount": ta.get("cent", 0)},
            "merchant": {
                "reference_merchant_id": merchant.get("referenceMerchantId", merchant.get("merchantId", "")),
                "merchant_name": merchant.get("merchantName", ""),
                "merchant_mcc": merchant.get("merchantMcc", ""),
            },
        }
    goods = checkout.get("goods")
    if goods:
        result["goods"] = goods
    return result


def _normalize_value(v: Any) -> Any:
    """Normalize a value for canonical JSON: strip strings, recurse into dicts/lists."""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, dict):
        return {k: _normalize_value(val) for k, val in sorted(v.items())}
    if isinstance(v, list):
        return [_normalize_value(item) for item in v]
    return v


def _canonical_json(data: Any) -> str:
    """Produce canonical JSON: sorted keys, no whitespace, normalized values."""
    return json.dumps(_normalize_value(data), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _compute_checkout_hash(data: Any) -> str:
    """Compute checkout hash: B64U(SHA-256(canonical_json(normalized(data))))."""
    canonical = _canonical_json(data)
    digest = hashlib.sha256(canonical.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
