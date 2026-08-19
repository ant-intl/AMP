"""Persistence stores and SQLite models extracted from mandate.py.

This module consolidates all storage-related concerns:
  - SQLite model definitions (TokenModel, MandateModel, PaymentTokenModel, CheckoutModel, PaymentOrderModel)
  - Repository classes (_MandateRepo, _TokenStore)
  - In-memory stores (_SessionStore, _IdempotencyStore)
  - Helper exception (_DuplicateKeyError)
  - Enums: TokenStatus, PaymentTokenStatus, PaymentOrderStatus, _CheckoutExtKey
  - Path constants used by stores

All persistent data shares a single SQLite database at TOKEN_STORE_PATH,
which contains five tables: token, mandate, payment_token, checkout, and payment_order.

The token table carries three lifecycle fields (expiry_time, psp_id, token_status)
that are populated during enrollment and validated during applyCredential.

The mandate service (mandate.py) imports and instantiates these classes.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from common.multi_currency_money import MultiCurrencyMoney
from common.sqlite_store import SqliteModel, SqliteRepo
from common.utils import gen_id
from schemas.checkout import CartInfo, Checkout, Merchant
from schemas.mandate import (
    AuthSignatureInfo,
    Budget,
    Mandate,
    MandateConstraints,
    MandateExtendType,
    MandateStatus,
    MandateType,
    dt_to_iso,
    money_from_dict,
    money_to_dict,
    parse_dt_safe,
)

logger = logging.getLogger("mandate.store")

# ---------------------------------------------------------------------------
# SQLite-backed persistence paths (from environment variables)
# When empty, SqliteRepo uses a pure in-memory SQLite database.
# ---------------------------------------------------------------------------
TOKEN_STORE_PATH: str = os.environ.get("TOKEN_STORE_PATH", "")


# ---------------------------------------------------------------------------
# Enums & constants used by stores
# ---------------------------------------------------------------------------

class TokenStatus(str, Enum):
    """Token lifecycle status."""
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    INACTIVE = "INACTIVE"


class PaymentTokenStatus(str, Enum):
    """Payment token lifecycle status."""
    ISSUED = "ISSUED"
    USED = "USED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class PaymentOrderStatus(str, Enum):
    """Payment order lifecycle status."""
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"
    CLOSED = "CLOSED"


class _CheckoutExtKey(str, Enum):
    """Ext_info keys used in Checkout ext_info (JSON field)."""
    TOKEN_ID = "tokenId"
    RECORD_TYPE = "recordType"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_money(m: Any) -> MultiCurrencyMoney:
    """Convert a _MoneyIn-like object to MultiCurrencyMoney."""
    return MultiCurrencyMoney.of(m.cent, m.currency)


# ===================================================================
# SQLite persistent model classes
# ===================================================================


class TokenModel(SqliteModel):
    """Enrollment token record — created when MPP completes binding IDV.

    Columns map directly to the fields stored via ``_TokenStore.store_token``.
    Complex values (``isp_pk`` JWK dict) are persisted as JSON TEXT.
    """

    def __init__(
        self,
        token_id: str = "",
        l1_serialized: str = "",
        session_id: str = "",
        customer_id: str = "",
        isp_pk: str | None = None,
        expiry_time: str | None = None,
        psp_id: str = "",
        token_status: str | None = None,
        gmt_create: str | None = None,
        gmt_modified: str | None = None,
    ) -> None:
        self.token_id = token_id
        self.l1_serialized = l1_serialized
        self.session_id = session_id
        self.customer_id = customer_id
        self.isp_pk = isp_pk
        self.expiry_time = expiry_time
        self.psp_id = psp_id
        self.token_status = token_status
        self.gmt_create = gmt_create
        self.gmt_modified = gmt_modified

    @property
    def table_name(self) -> str:
        return "token"

    @property
    def pk_column(self) -> str:
        return "token_id"

    @classmethod
    def columns(cls) -> list[tuple[str, str]]:
        return [
            ("token_id",      "TEXT PRIMARY KEY"),
            ("l1_serialized", "TEXT"),
            ("session_id",    "TEXT"),
            ("customer_id",   "TEXT"),
            ("isp_pk",        "TEXT"),
            ("expiry_time",   "TEXT"),
            ("psp_id",        "TEXT"),
            ("token_status",  "TEXT"),
            ("gmt_create",    "TEXT"),
            ("gmt_modified",  "TEXT"),
        ]

    def to_row(self) -> dict[str, Any]:
        return {
            "token_id":      self.token_id,
            "l1_serialized": self.l1_serialized,
            "session_id":    self.session_id,
            "customer_id":   self.customer_id,
            "isp_pk":        self.isp_pk,
            "expiry_time":   self.expiry_time,
            "psp_id":        self.psp_id,
            "token_status":  self.token_status,
            "gmt_create":    self.gmt_create,
            "gmt_modified":  self.gmt_modified,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> TokenModel:
        return cls(
            token_id=row.get("token_id") or "",
            l1_serialized=row.get("l1_serialized") or "",
            session_id=row.get("session_id") or "",
            customer_id=row.get("customer_id") or "",
            isp_pk=row.get("isp_pk"),
            expiry_time=row.get("expiry_time"),
            psp_id=row.get("psp_id") or "",
            token_status=row.get("token_status"),
            gmt_create=row.get("gmt_create"),
            gmt_modified=row.get("gmt_modified"),
        )


class PaymentTokenModel(SqliteModel):
    """Payment token — issued by ``applyCredential`` for each checkout payment.

    Links the one-time ``payment_token`` back to the originating mandate and token,
    and persists the raw checkout context for audit / reconciliation.

    Lifecycle fields:
      - ``payment_status``: ISSUED → USED / EXPIRED / FAILED
      - ``expiry_time``:    ISO-8601 timestamp after which the token is no longer valid
      - ``payment_result``: JSON TEXT — raw result payload returned by the Network service

    Verifiable authorization:
      - ``l3_serialized``:  L3 SD-JWT (Agent signature) for the verifiable authorization chain
    """

    def __init__(
        self,
        payment_token: str = "",
        mandate_id: str = "",
        token_id: str = "",
        checkout: str | None = None,
        payment_status: str | None = None,
        expiry_time: str | None = None,
        payment_result: str | None = None,
        l3_serialized: str | None = None,
        gmt_create: str | None = None,
        gmt_modified: str | None = None,
    ) -> None:
        self.payment_token = payment_token
        self.mandate_id = mandate_id
        self.token_id = token_id
        self.checkout = checkout
        self.payment_status = payment_status
        self.expiry_time = expiry_time
        self.payment_result = payment_result
        self.l3_serialized = l3_serialized
        self.gmt_create = gmt_create
        self.gmt_modified = gmt_modified

    @property
    def table_name(self) -> str:
        return "payment_token"

    @property
    def pk_column(self) -> str:
        return "payment_token"

    @classmethod
    def columns(cls) -> list[tuple[str, str]]:
        return [
            ("payment_token",  "TEXT PRIMARY KEY"),
            ("mandate_id",     "TEXT"),
            ("token_id",       "TEXT"),
            ("checkout",       "TEXT"),
            ("payment_status", "TEXT"),
            ("expiry_time",    "TEXT"),
            ("payment_result", "TEXT"),
            ("l3_serialized",  "TEXT"),
            ("gmt_create",     "TEXT"),
            ("gmt_modified",   "TEXT"),
        ]

    def to_row(self) -> dict[str, Any]:
        return {
            "payment_token":  self.payment_token,
            "mandate_id":     self.mandate_id,
            "token_id":       self.token_id,
            "checkout":       self.checkout,
            "payment_status": self.payment_status,
            "expiry_time":    self.expiry_time,
            "payment_result": self.payment_result,
            "l3_serialized":  self.l3_serialized,
            "gmt_create":     self.gmt_create,
            "gmt_modified":   self.gmt_modified,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> PaymentTokenModel:
        return cls(
            payment_token=row.get("payment_token") or "",
            mandate_id=row.get("mandate_id") or "",
            token_id=row.get("token_id") or "",
            checkout=row.get("checkout"),
            payment_status=row.get("payment_status"),
            expiry_time=row.get("expiry_time"),
            payment_result=row.get("payment_result"),
            l3_serialized=row.get("l3_serialized"),
            gmt_create=row.get("gmt_create"),
            gmt_modified=row.get("gmt_modified"),
        )


class PaymentOrderModel(SqliteModel):
    """Payment order record — created when ``process_payment`` settles a checkout.

    Tracks the payment lifecycle: amount, currency, and status.

    Lifecycle:
      - ``status``: PENDING → SUCCESS / FAIL → CLOSED
    """

    def __init__(
        self,
        payment_id: str = "",
        acquirer_order_id: str = "",
        amount: int = 0,
        currency: str = "",
        status: str | None = None,
        gmt_create: str | None = None,
        gmt_modified: str | None = None,
    ) -> None:
        self.payment_id = payment_id
        self.acquirer_order_id = acquirer_order_id
        self.amount = amount
        self.currency = currency
        self.status = status
        self.gmt_create = gmt_create
        self.gmt_modified = gmt_modified

    @property
    def table_name(self) -> str:
        return "payment_order"

    @property
    def pk_column(self) -> str:
        return "payment_id"

    @classmethod
    def columns(cls) -> list[tuple[str, str]]:
        return [
            ("payment_id",         "TEXT PRIMARY KEY"),
            ("acquirer_order_id",  "TEXT"),
            ("amount",             "INTEGER"),
            ("currency",           "TEXT"),
            ("status",             "TEXT"),
            ("gmt_create",         "TEXT"),
            ("gmt_modified",       "TEXT"),
        ]

    def to_row(self) -> dict[str, Any]:
        return {
            "payment_id":         self.payment_id,
            "acquirer_order_id":  self.acquirer_order_id,
            "amount":             self.amount,
            "currency":           self.currency,
            "status":             self.status,
            "gmt_create":         self.gmt_create,
            "gmt_modified":       self.gmt_modified,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> PaymentOrderModel:
        return cls(
            payment_id=row.get("payment_id") or "",
            acquirer_order_id=row.get("acquirer_order_id") or "",
            amount=row.get("amount") or 0,
            currency=row.get("currency") or "",
            status=row.get("status"),
            gmt_create=row.get("gmt_create"),
            gmt_modified=row.get("gmt_modified"),
        )


class CheckoutModel(Checkout, SqliteModel):
    """Persistent Checkout model with explicit SQLite column schema.

    Domain-level fields map to declared SQLite columns.  Complex nested
    objects (Merchant, CartInfo) are stored as JSON TEXT columns — their
    internal fields are NOT separate top-level columns.
    """

    @property
    def table_name(self) -> str:
        return "checkout"

    @property
    def pk_column(self) -> str:
        return "checkout_id"

    @classmethod
    def columns(cls) -> list[tuple[str, str]]:
        return [
            ("checkout_id",           "TEXT PRIMARY KEY"),
            ("mandate_id",            "TEXT"),
            ("merchant",              "TEXT"),
            ("cart_info",             "TEXT"),
            ("checkout_hash",         "TEXT"),
            ("ext_info",              "TEXT"),
            ("reference_checkout_id", "TEXT"),
            ("gmt_create",            "TEXT"),
            ("gmt_modified",          "TEXT"),
        ]

    # -- Row conversion --

    def to_row(self) -> dict[str, Any]:
        merchant_json: str | None = None
        if self.merchant is not None:
            merchant_json = json.dumps({
                "reference_merchant_id": self.merchant.reference_merchant_id,
                "merchant_name": self.merchant.merchant_name,
                "merchant_mcc": self.merchant.merchant_mcc,
                "merchant_web_site_url": self.merchant.merchant_web_site_url,
                "store_name": self.merchant.store_name,
            }, ensure_ascii=False)
        cart_json: str | None = None
        if self.cart_info is not None:
            cart_json = json.dumps({
                "total_amount": money_to_dict(self.cart_info.total_amount),
                "item_count": self.cart_info.item_count,
                "items": self.cart_info.items,
            }, ensure_ascii=False)
        return {
            "checkout_id":           self.checkout_id,
            "mandate_id":            self.mandate_id,
            "merchant":              merchant_json,
            "cart_info":             cart_json,
            "checkout_hash":         self.checkout_hash,
            "ext_info":              self.ext_info,
            "reference_checkout_id": self.reference_checkout_id,
            "gmt_create":            dt_to_iso(self.gmt_create),
            "gmt_modified":          dt_to_iso(self.gmt_modified),
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> CheckoutModel:
        md = json.loads(row["merchant"]) if row.get("merchant") else None
        merchant = Merchant(
            reference_merchant_id=md.get("reference_merchant_id"),
            merchant_name=md.get("merchant_name"),
            merchant_mcc=md.get("merchant_mcc"),
            merchant_web_site_url=md.get("merchant_web_site_url"),
            store_name=md.get("store_name"),
        ) if md else None
        cd = json.loads(row["cart_info"]) if row.get("cart_info") else None
        cart_info = CartInfo(
            total_amount=money_from_dict(cd.get("total_amount")),
            item_count=cd.get("item_count"),
            items=cd.get("items"),
        ) if cd else None
        c = cls()
        c.checkout_id = row.get("checkout_id")
        c.mandate_id = row.get("mandate_id")
        c.merchant = merchant
        c.cart_info = cart_info
        c.checkout_hash = row.get("checkout_hash")
        c.ext_info = row.get("ext_info")
        c.reference_checkout_id = row.get("reference_checkout_id")
        c.gmt_create = parse_dt_safe(row.get("gmt_create"))
        c.gmt_modified = parse_dt_safe(row.get("gmt_modified"))
        return c


class MandateModel(Mandate, SqliteModel):
    """Persistent Mandate model with explicit SQLite column schema.

    Each field of the Mandate dataclass maps to a declared SQLite column.
    Complex nested objects (Budget, AuthSignatureInfo, MandateConstraints,
    ext_info) are stored as JSON TEXT.
    """

    @property
    def table_name(self) -> str:
        return "mandate"

    @property
    def pk_column(self) -> str:
        return "mandate_id"

    @classmethod
    def columns(cls) -> list[tuple[str, str]]:
        return [
            ("mandate_id",               "TEXT PRIMARY KEY"),
            ("token",                    "TEXT"),
            ("mandate_type",             "TEXT"),
            ("mandate_status",           "TEXT"),
            ("expiry_time",              "TEXT"),
            ("description",              "TEXT"),
            ("raw",                      "TEXT"),
            ("budget",                   "TEXT"),
            ("constraints",              "TEXT"),
            ("checkout_hash",            "TEXT"),
            ("authentication_signature", "TEXT"),
            ("revoked_time",             "TEXT"),
            ("closed_time",              "TEXT"),
            ("ext_info",                 "TEXT"),
            ("gmt_create",               "TEXT"),
            ("gmt_modified",             "TEXT"),
        ]

    # -- Row conversion --

    def to_row(self) -> dict[str, Any]:
        budget_json: str | None = None
        if self.budget is not None:
            budget_json = json.dumps({
                "total_budget_amount": money_to_dict(self.budget.total_budget_amount),
                "used_amount": money_to_dict(self.budget.used_amount),
                "remaining_amount": money_to_dict(self.budget.remaining_amount),
                "usage_ratio": self.budget.usage_ratio,
            }, ensure_ascii=False)
        constraints_json: str | None = None
        if self.constraints is not None:
            constraints_json = json.dumps({
                "merchant_name_list": list(self.constraints.merchant_name_list),
                "merchant_mcc_list": list(self.constraints.merchant_mcc_list),
            }, ensure_ascii=False)
        auth_json: str | None = None
        if self.authentication_signature is not None:
            a = self.authentication_signature
            auth_json = json.dumps({
                "challenge": a.challenge,
                "assurance_data": a.assurance_data,
                "authentication_type": a.authentication_type,
                "authentication_id": a.authentication_id,
                "customer_id": a.customer_id,
                "wallet_masked_login_id": a.wallet_masked_login_id,
                "challenge_raw": a.challenge_raw,
            }, ensure_ascii=False)
        # ext_info: convert enum keys to string keys
        ext: dict[str, str] = {}
        for k, v in self.ext_info.items():
            key_str = k.value if isinstance(k, Enum) else str(k)
            ext[key_str] = v
        ext_json = json.dumps(ext, ensure_ascii=False) if ext else None

        return {
            "mandate_id":               self.mandate_id,
            "token":                    self.token,
            "mandate_type":             self.mandate_type.value if self.mandate_type else None,
            "mandate_status":           self.mandate_status.value if self.mandate_status else None,
            "expiry_time":              dt_to_iso(self.expiry_time),
            "description":              self.description,
            "raw":                      self.raw,
            "budget":                   budget_json,
            "constraints":              constraints_json,
            "checkout_hash":            self.checkout_hash,
            "authentication_signature": auth_json,
            "revoked_time":             dt_to_iso(self.revoked_time),
            "closed_time":              dt_to_iso(self.closed_time),
            "ext_info":                 ext_json,
            "gmt_create":               dt_to_iso(self.gmt_create),
            "gmt_modified":             dt_to_iso(self.gmt_modified),
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> MandateModel:
        m = cls()
        m.mandate_id = row.get("mandate_id")
        m.token = row.get("token")
        mt = row.get("mandate_type")
        m.mandate_type = MandateType(mt) if mt else None
        ms = row.get("mandate_status")
        m.mandate_status = MandateStatus(ms) if ms else None
        m.expiry_time = parse_dt_safe(row.get("expiry_time"))
        m.description = row.get("description")
        m.raw = row.get("raw")
        # Budget
        bd = json.loads(row["budget"]) if row.get("budget") else None
        if bd is not None:
            b = Budget()
            b.total_budget_amount = money_from_dict(bd.get("total_budget_amount"))
            b.used_amount = money_from_dict(bd.get("used_amount"))
            b.remaining_amount = money_from_dict(bd.get("remaining_amount"))
            b.usage_ratio = bd.get("usage_ratio")
            m.budget = b
        # Constraints
        cd = json.loads(row["constraints"]) if row.get("constraints") else None
        if cd is not None:
            m.constraints = MandateConstraints(
                merchant_name_list=cd.get("merchant_name_list", []),
                merchant_mcc_list=cd.get("merchant_mcc_list", []),
            )
        m.checkout_hash = row.get("checkout_hash")
        # AuthSignatureInfo
        ad = json.loads(row["authentication_signature"]) if row.get("authentication_signature") else None
        if ad is not None:
            m.authentication_signature = AuthSignatureInfo(
                challenge=ad.get("challenge"),
                assurance_data=ad.get("assurance_data"),
                authentication_type=ad.get("authentication_type"),
                authentication_id=ad.get("authentication_id"),
                customer_id=ad.get("customer_id"),
                wallet_masked_login_id=ad.get("wallet_masked_login_id"),
                challenge_raw=ad.get("challenge_raw"),
            )
        m.revoked_time = parse_dt_safe(row.get("revoked_time"))
        m.closed_time = parse_dt_safe(row.get("closed_time"))
        # ext_info: restore enum keys where possible
        ext_raw = json.loads(row["ext_info"]) if row.get("ext_info") else {}
        ext: dict[MandateExtendType | str, str] = {}
        for k, v in ext_raw.items():
            resolved = MandateExtendType.get_by_code(k)
            ext[resolved if resolved is not None else k] = v
        m.ext_info = ext
        m.gmt_create = parse_dt_safe(row.get("gmt_create"))
        m.gmt_modified = parse_dt_safe(row.get("gmt_modified"))
        return m


# ===================================================================
# In-memory stores
# ===================================================================


class _DuplicateKeyError(Exception):
    pass


class _IdempotencyStore:
    """In-memory idempotency key store (no persistence)."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, str]] = {}
        self._lock = threading.Lock()

    def query_or_insert(self, key: str, info: dict[str, str]) -> dict[str, str]:
        with self._lock:
            if key in self._store:
                return copy.deepcopy(self._store[key])
            self._store[key] = copy.deepcopy(info)
            return copy.deepcopy(info)


class _SessionStore:
    """In-memory session store (no persistence — sessions are ephemeral)."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create(self, auth_context: str, **kwargs: Any) -> str:
        session_id = gen_id()
        with self._lock:
            self._data[session_id] = {
                "session_id": session_id,
                "auth_context": auth_context,
                "status": "CREATED",
                **kwargs,
            }
        return session_id

    def get(self, session_id: str) -> dict[str, Any] | None:
        with self._lock:
            v = self._data.get(session_id)
            return copy.deepcopy(v) if v else None

    def update(self, session_id: str, **kwargs: Any) -> None:
        with self._lock:
            existing = self._data.get(session_id)
            if existing is not None:
                existing.update(kwargs)


# ===================================================================
# Persistent repositories
# ===================================================================


class _MandateRepo:
    """Schema-aware Mandate repository backed by SqliteRepo[MandateModel]."""

    def __init__(self) -> None:
        self._repo = SqliteRepo(TOKEN_STORE_PATH, MandateModel)

    def save(self, mandate: Mandate) -> None:
        model = mandate if isinstance(mandate, MandateModel) else self._to_model(mandate)
        if not self._repo.save_if_absent(model):
            raise _DuplicateKeyError()

    def query(self, mandate_id: str) -> Mandate | None:
        return self._repo.get(mandate_id)

    def lock(self, mandate_id: str) -> Mandate | None:
        self._repo.acquire()
        return self._repo.get_locked(mandate_id)

    def update(self, mandate: Mandate) -> None:
        model = mandate if isinstance(mandate, MandateModel) else self._to_model(mandate)
        self._repo.save_locked(model)

    def release(self) -> None:
        self._repo.release()

    @staticmethod
    def _to_model(m: Mandate) -> MandateModel:
        """Copy fields from a plain Mandate into a MandateModel instance."""
        model = MandateModel()
        for f in Mandate.__dataclass_fields__:
            setattr(model, f, getattr(m, f))
        return model


class _TokenStore:
    """Unified repository facade for mandate/token persistent entities.

    Manages four tables — **token**, **mandate**, **payment_token**, and **checkout** —
    all sharing a single SQLite database file at ``TOKEN_STORE_PATH``.
    Each table is backed by its own ``SqliteRepo`` instance with a dedicated ``SqliteModel`` subclass.

    **Entities and their methods:**

    *Token* (enrollment binding record — ``TokenModel``):
        - ``store_token(token_id, **kwargs)`` — persist a new enrollment token with lifecycle
          fields (``expiry_time``, ``psp_id``, ``token_status``).
        - ``get_by_token_id(token_id)`` — look up by PK, returns a flat ``dict``.

    *Mandate association* (enriches ``MandateModel`` records created by ``MandateService``):
        - ``store_mandate(mandate_id, token_id, **kwargs)`` — attach token-association fields
          (``l2_serialized``, ``session_id``, ``checkout``) to an existing mandate's ``ext_info``.
        - ``get_by_mandate_id(mandate_id)`` — look up and extract token-association fields.

    *Payment token* (one-time credential issued by ``applyCredential`` — ``PaymentTokenModel``):
        - ``store_payment_token(payment_token, **kwargs)`` — issue a new payment token with
          lifecycle fields (``payment_status``, ``expiry_time``, ``payment_result``).
        - ``update_payment_token(payment_token, **kwargs)`` — update lifecycle fields in place.
        - ``get_payment_token(payment_token)`` — look up by PK, returns a flat ``dict``.

    *Checkout* (structured checkout record — ``CheckoutModel``):
        - ``build_checkout(...)`` *(static)* — build a ``Checkout`` domain object from a raw
          camelCase dict, populating ``CartInfo``, ``Merchant``, and ``ext_info``.
        - ``save_checkout(checkout)`` — persist a ``Checkout`` record.
        - ``get_checkout(checkout_id)`` — look up by PK (``checkout_id == payment_token``).

    **Design notes:**
      - Complex nested values (``isp_pk`` JWK dict, ``checkout`` dict, ``payment_result`` dict)
        are serialised to JSON TEXT on write and parsed back on read so callers see plain dicts.
      - The mandate table uses the shared ``MandateModel`` from ``schemas.mandate``; token-specific
        association fields (``l2_serialized``, ``session_id``, ``checkout``) are stored in the
        mandate's ``ext_info`` JSON field rather than as separate columns.
    """

    def __init__(self) -> None:
        self._tokens: SqliteRepo[TokenModel] = SqliteRepo(TOKEN_STORE_PATH, TokenModel)
        self._mandates: SqliteRepo[MandateModel] = SqliteRepo(TOKEN_STORE_PATH, MandateModel)
        self._payment_tokens: SqliteRepo[PaymentTokenModel] = SqliteRepo(TOKEN_STORE_PATH, PaymentTokenModel)
        self._checkouts: SqliteRepo[CheckoutModel] = SqliteRepo(TOKEN_STORE_PATH, CheckoutModel)

    # -- Token (enrollment binding record) --

    def store_token(self, token_id: str, **kwargs: Any) -> None:
        isp_pk_raw = kwargs.get("isp_pk")
        # Resolve token_status: accept TokenStatus enum or raw string, default to ACTIVE
        raw_status = kwargs.get("token_status")
        if raw_status is None:
            token_status = TokenStatus.ACTIVE.value
        elif isinstance(raw_status, TokenStatus):
            token_status = raw_status.value
        else:
            token_status = str(raw_status)
        # Resolve expiry_time: accept datetime or ISO string
        raw_expiry = kwargs.get("expiry_time")
        if isinstance(raw_expiry, datetime):
            expiry_time = dt_to_iso(raw_expiry)
        elif raw_expiry is not None:
            expiry_time = str(raw_expiry)
        else:
            expiry_time = None
        now = dt_to_iso(datetime.now(timezone.utc))
        # Preserve original gmt_create if the token already exists (INSERT OR REPLACE)
        existing = self._tokens.get(token_id)
        gmt_create = existing.gmt_create if existing is not None else now
        self._tokens.save(TokenModel(
            token_id=token_id,
            l1_serialized=kwargs.get("l1_serialized", ""),
            session_id=kwargs.get("session_id", ""),
            customer_id=kwargs.get("customer_id", ""),
            isp_pk=json.dumps(isp_pk_raw, ensure_ascii=False) if isp_pk_raw is not None else None,
            expiry_time=expiry_time,
            psp_id=kwargs.get("psp_id", ""),
            token_status=token_status,
            gmt_create=gmt_create,
            gmt_modified=now,
        ))

    def get_by_token_id(self, token_id: str) -> dict[str, Any] | None:
        model = self._tokens.get(token_id)
        if model is None:
            return None
        isp_pk = json.loads(model.isp_pk) if model.isp_pk else None
        return {
            "token_id":      model.token_id,
            "l1_serialized": model.l1_serialized,
            "session_id":    model.session_id,
            "customer_id":   model.customer_id,
            "isp_pk":        isp_pk,
            "expiry_time":   model.expiry_time,
            "psp_id":        model.psp_id,
            "token_status":  model.token_status,
            "gmt_create":    model.gmt_create,
            "gmt_modified":  model.gmt_modified,
        }

    # -- Mandate association (enriches the MandateModel record created by MandateService) --

    def store_mandate(self, mandate_id: str, token_id: str, **kwargs: Any) -> None:
        """Enrich an existing MandateModel record with token-association fields.

        The mandate record must already exist (created by MandateService.create_mandate).
        This method reads it, adds l2_serialized / session_id / checkout to ext_info,
        and saves it back.
        """
        existing = self._mandates.get(mandate_id)
        if existing is None:
            # Fallback: create a new record if not found (e.g. standalone usage)
            existing = MandateModel()
            existing.mandate_id = mandate_id
            existing.token = token_id
            existing.mandate_status = MandateStatus.ACTIVE
            now = datetime.now(timezone.utc)
            existing.gmt_create = now
            existing.gmt_modified = now

        # Store mandate_type if provided (from network orchestration layer)
        mandate_type = kwargs.get("mandate_type")
        if mandate_type and not existing.mandate_type:
            from schemas.mandate import MandateType
            try:
                existing.mandate_type = MandateType(mandate_type)
            except ValueError:
                pass

        # Store token-association fields in ext_info
        l2_serialized = kwargs.get("l2_serialized", "")
        if l2_serialized:
            existing.put_ext_info(MandateExtendType.L2_SERIALIZED, l2_serialized)
        session_id = kwargs.get("session_id", "")
        if session_id:
            existing.put_ext_info(MandateExtendType.SESSION_ID, session_id)
        checkout_raw = kwargs.get("checkout")
        if checkout_raw is not None:
            existing.put_ext_info(
                MandateExtendType.CHECKOUT_RAW,
                json.dumps(checkout_raw, ensure_ascii=False),
            )
        existing.gmt_modified = datetime.now(timezone.utc)
        self._mandates.save(existing)

    def get_by_mandate_id(self, mandate_id: str) -> dict[str, Any] | None:
        """Look up a mandate by ID and return a dict with token-association fields.

        Returns token_id, mandate_type, l2_serialized, session_id, and checkout
        extracted from the MandateModel and its ext_info.
        """
        model = self._mandates.get(mandate_id)
        if model is None:
            return None
        l2_serialized = model.fetch_ext_info(MandateExtendType.L2_SERIALIZED) or ""
        session_id = model.fetch_ext_info(MandateExtendType.SESSION_ID) or ""
        checkout_raw_str = model.fetch_ext_info(MandateExtendType.CHECKOUT_RAW)
        checkout = json.loads(checkout_raw_str) if checkout_raw_str else {}
        return {
            "mandate_id":    model.mandate_id,
            "token_id":      model.token or "",
            "l2_serialized": l2_serialized,
            "session_id":    session_id,
            "mandate_type":  model.mandate_type.value if model.mandate_type else "",
            "checkout":      checkout,
        }

    # -- Payment token --

    def store_payment_token(self, payment_token: str, **kwargs: Any) -> None:
        checkout_raw = kwargs.get("checkout")
        # Resolve payment_status: accept PaymentTokenStatus enum or raw string, default to ISSUED
        raw_status = kwargs.get("payment_status")
        if raw_status is None:
            payment_status = PaymentTokenStatus.ISSUED.value
        elif isinstance(raw_status, PaymentTokenStatus):
            payment_status = raw_status.value
        else:
            payment_status = str(raw_status)
        # Resolve expiry_time: accept datetime or ISO string
        raw_expiry = kwargs.get("expiry_time")
        if isinstance(raw_expiry, datetime):
            expiry_time = dt_to_iso(raw_expiry)
        elif raw_expiry is not None:
            expiry_time = str(raw_expiry)
        else:
            expiry_time = None
        # Resolve payment_result: accept dict or raw string
        raw_result = kwargs.get("payment_result")
        if isinstance(raw_result, dict):
            payment_result = json.dumps(raw_result, ensure_ascii=False)
        elif raw_result is not None:
            payment_result = str(raw_result)
        else:
            payment_result = None
        now = dt_to_iso(datetime.now(timezone.utc))
        # Preserve original gmt_create if the payment token already exists (INSERT OR REPLACE)
        existing = self._payment_tokens.get(payment_token)
        gmt_create = existing.gmt_create if existing is not None else now
        self._payment_tokens.save(PaymentTokenModel(
            payment_token=payment_token,
            mandate_id=kwargs.get("mandate_id", ""),
            token_id=kwargs.get("token_id", ""),
            checkout=json.dumps(checkout_raw, ensure_ascii=False) if checkout_raw is not None else None,
            payment_status=payment_status,
            expiry_time=expiry_time,
            payment_result=payment_result,
            l3_serialized=kwargs.get("l3_serialized"),
            gmt_create=gmt_create,
            gmt_modified=now,
        ))
        # Also persist a structured Checkout record (checkout_id == payment_token)
        if checkout_raw:
            co = self.build_checkout(
                checkout_id=payment_token,
                mandate_id=kwargs.get("mandate_id", ""),
                raw_checkout=checkout_raw,
                token_id=kwargs.get("token_id", ""),
                record_type="PAYMENT_TOKEN_CHECKOUT",
            )
            self.save_checkout(co)

    def update_payment_token(self, payment_token: str, **kwargs: Any) -> None:
        """Update lifecycle fields of an existing payment token (status, result, expiry_time).

        Only the supplied keyword arguments are updated; others are left untouched.
        """
        model = self._payment_tokens.get(payment_token)
        if model is None:
            return
        if "payment_status" in kwargs:
            raw_status = kwargs["payment_status"]
            if isinstance(raw_status, PaymentTokenStatus):
                model.payment_status = raw_status.value
            else:
                model.payment_status = str(raw_status)
        if "payment_result" in kwargs:
            raw_result = kwargs["payment_result"]
            if isinstance(raw_result, dict):
                model.payment_result = json.dumps(raw_result, ensure_ascii=False)
            elif raw_result is not None:
                model.payment_result = str(raw_result)
            else:
                model.payment_result = None
        if "expiry_time" in kwargs:
            raw_expiry = kwargs["expiry_time"]
            if isinstance(raw_expiry, datetime):
                model.expiry_time = dt_to_iso(raw_expiry)
            elif raw_expiry is not None:
                model.expiry_time = str(raw_expiry)
            else:
                model.expiry_time = None
        model.gmt_modified = dt_to_iso(datetime.now(timezone.utc))
        self._payment_tokens.save(model)

    def get_payment_token(self, payment_token: str) -> dict[str, Any] | None:
        """Look up a payment token record and return a flat dict."""
        model = self._payment_tokens.get(payment_token)
        if model is None:
            return None
        # Deserialize payment_result JSON back to dict when possible
        payment_result = model.payment_result
        if payment_result:
            try:
                payment_result = json.loads(payment_result)
            except (json.JSONDecodeError, TypeError):
                pass
        return {
            "payment_token":  model.payment_token,
            "mandate_id":     model.mandate_id,
            "token_id":       model.token_id,
            "checkout":       json.loads(model.checkout) if model.checkout else None,
            "payment_status": model.payment_status,
            "expiry_time":    model.expiry_time,
            "payment_result": payment_result,
            "l3_serialized":  model.l3_serialized,
            "gmt_create":     model.gmt_create,
            "gmt_modified":   model.gmt_modified,
        }

    # -- Checkout --

    @staticmethod
    def build_checkout(
        checkout_id: str,
        mandate_id: str,
        raw_checkout: dict[str, Any],
        checkout_hash: str = "",
        token_id: str = "",
        record_type: str = "MANDATE_CHECKOUT",
    ) -> Checkout:
        """Build a Checkout domain object from a raw camelCase checkout dict.

        Converts totalAmount -> CartInfo, merchant -> Merchant, and stores
        token_id / record_type in ext_info for querying.
        """
        ta = raw_checkout.get("totalAmount", {})
        cart_info: CartInfo | None = None
        if ta:
            currency = ta.get("currency", "USD")
            cent = ta.get("cent", 0)
            cart_info = CartInfo(
                total_amount=MultiCurrencyMoney.of(cent, currency),
                item_count=ta.get("itemCount"),
                items=json.dumps(raw_checkout.get("goods")) if raw_checkout.get("goods") else None,
            )

        merchant_d = raw_checkout.get("merchant", {})
        merchant: Merchant | None = None
        if merchant_d:
            merchant = Merchant(
                reference_merchant_id=merchant_d.get("merchantId"),
                merchant_name=merchant_d.get("merchantName"),
                merchant_mcc=merchant_d.get("merchantMcc"),
                merchant_web_site_url=merchant_d.get("merchantWebSiteUrl"),
                store_name=merchant_d.get("storeName"),
            )

        now = datetime.now(timezone.utc)
        checkout = Checkout(
            checkout_id=checkout_id,
            mandate_id=mandate_id,
            merchant=merchant,
            cart_info=cart_info,
            checkout_hash=checkout_hash or None,
            gmt_create=now,
            gmt_modified=now,
        )
        # Store token_id and record_type in ext_info for traceability
        ext_data: dict[str, str] = {}
        if token_id:
            ext_data[_CheckoutExtKey.TOKEN_ID.value] = token_id
        ext_data[_CheckoutExtKey.RECORD_TYPE.value] = record_type
        checkout.ext_info = json.dumps(ext_data, ensure_ascii=False)
        return checkout

    def save_checkout(self, checkout: Checkout) -> None:
        """Persist a Checkout record."""
        model = checkout if isinstance(checkout, CheckoutModel) else self._checkout_to_model(checkout)
        self._checkouts.save(model)

    def get_checkout(self, checkout_id: str) -> Checkout | None:
        """Look up a Checkout record by its checkout_id (== payment_token)."""
        return self._checkouts.get(checkout_id)

    @staticmethod
    def _checkout_to_model(c: Checkout) -> CheckoutModel:
        """Copy fields from a plain Checkout into a CheckoutModel instance."""
        model = CheckoutModel()
        for f in Checkout.__dataclass_fields__:
            setattr(model, f, getattr(c, f))
        return model


# ===================================================================
# Payment order store
# ===================================================================


class _PaymentOrderStore:
    """SQLite-backed repository for payment order records.

    Manages the **payment_order** table independently of the mandate/token stores.

    Methods:
        - ``save(payment_id, ...)`` — persist a new payment order or overwrite an existing one.
        - ``update(payment_id, **kwargs)`` — update status.
        - ``get(payment_id)`` — look up by PK, returns a flat ``dict``.
        - ``list_all()`` — return all payment orders as a list of flat dicts.
        - ``delete(payment_id)`` — delete by PK.
        - ``clear()`` — delete all payment orders.
    """

    def __init__(self) -> None:
        self._repo: SqliteRepo[PaymentOrderModel] = SqliteRepo(TOKEN_STORE_PATH, PaymentOrderModel)

    def save(
        self,
        *,
        payment_id: str,
        acquirer_order_id: str = "",
        amount: int = 0,
        currency: str = "",
        status: str | PaymentOrderStatus | None = None,
    ) -> None:
        """Persist a new payment order or overwrite an existing one."""
        if status is None:
            status_str = PaymentOrderStatus.PENDING.value
        elif isinstance(status, PaymentOrderStatus):
            status_str = status.value
        else:
            status_str = str(status)
        now = dt_to_iso(datetime.now(timezone.utc))
        existing = self._repo.get(payment_id)
        gmt_create = existing.gmt_create if existing is not None else now
        self._repo.save(PaymentOrderModel(
            payment_id=payment_id,
            acquirer_order_id=acquirer_order_id,
            amount=amount,
            currency=currency,
            status=status_str,
            gmt_create=gmt_create,
            gmt_modified=now,
        ))

    def update(self, payment_id: str, **kwargs: Any) -> None:
        """Update specific fields of an existing payment order.

        Only the supplied keyword arguments are updated; others are left untouched.
        Supported keys: ``status``.
        """
        model = self._repo.get(payment_id)
        if model is None:
            return
        if "status" in kwargs:
            raw_status = kwargs["status"]
            if isinstance(raw_status, PaymentOrderStatus):
                model.status = raw_status.value
            else:
                model.status = str(raw_status)
        model.gmt_modified = dt_to_iso(datetime.now(timezone.utc))
        self._repo.save(model)

    def get(self, payment_id: str) -> dict[str, Any] | None:
        """Look up a payment order by payment_id and return a flat dict."""
        model = self._repo.get(payment_id)
        if model is None:
            return None
        return {
            "payment_id":         model.payment_id,
            "acquirer_order_id":  model.acquirer_order_id,
            "amount":             model.amount,
            "currency":           model.currency,
            "status":             model.status,
            "gmt_create":         model.gmt_create,
            "gmt_modified":       model.gmt_modified,
        }

    def get_by_acquirer_order_id(self, acquirer_order_id: str) -> dict[str, Any] | None:
        """Look up a payment order by acquirer_order_id for idempotency checks."""
        model = self._repo.find_by("acquirer_order_id", acquirer_order_id)
        if model is None:
            return None
        return {
            "payment_id":         model.payment_id,
            "acquirer_order_id":  model.acquirer_order_id,
            "amount":             model.amount,
            "currency":           model.currency,
            "status":             model.status,
            "gmt_create":         model.gmt_create,
            "gmt_modified":       model.gmt_modified,
        }

    def list_all(self) -> list[dict[str, Any]]:
        """Return all payment orders as a list of flat dicts."""
        results: list[dict[str, Any]] = []
        for model in self._repo.select_all():
            results.append({
                "payment_id":         model.payment_id,
                "acquirer_order_id":  model.acquirer_order_id,
                "amount":             model.amount,
                "currency":           model.currency,
                "status":             model.status,
                "gmt_create":         model.gmt_create,
                "gmt_modified":       model.gmt_modified,
            })
        return results

    def delete(self, payment_id: str) -> bool:
        """Delete a payment order by payment_id. Returns True if removed."""
        return self._repo.delete(payment_id)

    def clear(self) -> None:
        """Delete all payment orders."""
        for model in self._repo.select_all():
            self._repo.delete(model.payment_id)
