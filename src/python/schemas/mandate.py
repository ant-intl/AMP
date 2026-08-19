"""Mandate domain model."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from common.multi_currency_money import MultiCurrencyMoney


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class MandateStatus(str, Enum):
    """Mandate authorization status enum."""

    INACTIVE = "INACTIVE"  # Not yet activated
    ACTIVE = "ACTIVE"  # Active
    REVOKED = "REVOKED"  # Revoked
    EXPIRED = "EXPIRED"  # Expired
    CLOSED = "CLOSED"  # Closed

    @classmethod
    def get_by_code(cls, code: str) -> Optional["MandateStatus"]:
        """Get enum member by code, return None if not found."""
        for member in cls:
            if member.value == code:
                return member
        return None


class MandateType(str, Enum):
    """Mandate authorization type enum."""

    IMMEDIATE = "IMMEDIATE"  # Immediate authorization (human-present)
    AUTONOMOUS = "AUTONOMOUS"  # Autonomous authorization (human-not-present)

    @classmethod
    def get_by_code(cls, code: str) -> Optional["MandateType"]:
        """Get enum member by code, return None if not found."""
        for member in cls:
            if member.value == code:
                return member
        return None

    @classmethod
    def resolve_by_checkout(cls, checkout: object | None) -> "MandateType":
        """Derive mandateType from whether checkout is None.

        checkout is not None -> IMMEDIATE, None -> AUTONOMOUS.
        """
        return cls.IMMEDIATE if checkout is not None else cls.AUTONOMOUS


class MandateExtendType(str, Enum):
    """Enum for mandate ext_info field keys."""

    DEDUCTED = "Deducted"  # Deducted business idempotency ID list
    RELEASED = "Released"  # Released business idempotency ID list
    CHECKOUT_RAW = "CheckoutRaw"  # Checkout raw payload
    TSP_SESSION_ID = "TSP_SESSION_ID"  # tspSessionId
    L2_SERIALIZED = "L2Serialized"  # L2 SD-JWT packet from mandate IDV
    SESSION_ID = "SessionId"  # IDV session ID

    @classmethod
    def get_by_code(cls, code: str) -> Optional["MandateExtendType"]:
        """Get enum member by code, return None if not found."""
        if not code:
            return None
        for member in cls:
            if member.value == code:
                return member
        return None


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass
class AuthSignatureInfo:
    """
    Authentication signature value object.

    Encapsulates mandate authentication signature data including
    challenge, assurance data, and authentication type.
    """

    challenge: Optional[str] = None  # Challenge code
    assurance_data: Optional[str] = None  # Assurance data (JSON)
    authentication_type: Optional[str] = None  # Authentication type
    authentication_id: Optional[str] = None  # Wallet authentication session ID
    customer_id: Optional[str] = None  # Wallet-side user UID
    wallet_masked_login_id: Optional[str] = None  # Wallet login mask
    challenge_raw: Optional[str] = None  # Challenge raw payload

    def __repr__(self) -> str:
        return (
            f"AuthSignatureInfo(challenge={self.challenge!r}, "
            f"authentication_type={self.authentication_type!r})"
        )


@dataclass
class Budget:
    """
    Budget value object.

    Encapsulates mandate budget control information including
    total budget amount, used amount, and remaining amount.
    """

    total_budget_amount: Optional[MultiCurrencyMoney] = None  # Total budget amount
    used_amount: Optional[MultiCurrencyMoney] = None  # Used amount
    remaining_amount: Optional[MultiCurrencyMoney] = None  # Remaining amount
    usage_ratio: Optional[int] = None  # Usage ratio (usedAmount / totalBudgetAmount)

    def __repr__(self) -> str:
        return (
            f"Budget(total_budget_amount={self.total_budget_amount}, "
            f"used_amount={self.used_amount}, "
            f"remaining_amount={self.remaining_amount})"
        )


@dataclass
class MandateConstraints:
    """Mandate constraints."""

    merchant_name_list: list[str] = field(default_factory=list)  # Merchant name list
    merchant_mcc_list: list[str] = field(default_factory=list)  # Merchant MCC list

    def is_empty(self) -> bool:
        """Check if constraints are empty (both lists are empty)."""
        return not self.merchant_name_list and not self.merchant_mcc_list

    @classmethod
    def empty(cls) -> "MandateConstraints":
        """Create an empty MandateConstraints (both lists are empty)."""
        return cls(merchant_name_list=[], merchant_mcc_list=[])


# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------


@dataclass
class Mandate:
    """Mandate domain model."""

    mandate_id: Optional[str] = None  # Mandate ID
    token: Optional[str] = None  # Associated A+ Token
    mandate_type: Optional[MandateType] = None  # Mandate type
    mandate_status: Optional[MandateStatus] = None  # Mandate status
    expiry_time: Optional[datetime] = None  # Expiry time
    description: Optional[str] = None  # Description
    raw: Optional[str] = None  # Raw data (JSON)
    budget: Optional[Budget] = None  # Budget information
    constraints: Optional[MandateConstraints] = None  # Merchant constraints
    checkout_hash: Optional[str] = None  # Checkout hash
    authentication_signature: Optional[AuthSignatureInfo] = None  # Authentication signature info
    revoked_time: Optional[datetime] = None  # Revoked time
    closed_time: Optional[datetime] = None  # Closed time
    ext_info: dict[MandateExtendType, str] = field(default_factory=dict)  # Extension information
    gmt_create: Optional[datetime] = None  # Creation time
    gmt_modified: Optional[datetime] = None  # Modification time

    # ------------------------------------------------------------------
    # Extension info operations
    # ------------------------------------------------------------------

    def fetch_ext_info(self, key: MandateExtendType) -> Optional[str]:
        """
        Get extension info value.

        :param key: extension info key
        :return: extension info value, or None if not found
        """
        return self.ext_info.get(key)

    def put_ext_info(self, key: MandateExtendType, value: str) -> None:
        """
        Add extension info.

        :param key: extension info key
        :param value: extension info value (skipped if None)
        """
        if value is None:
            return
        self.ext_info[key] = value

    def fetch_ext_info_list(self, key: MandateExtendType) -> list[str]:
        """
        Get extension info as a list.

        :param key: extension info key
        :return: extension info list, or empty list if not found
        """
        value = self.fetch_ext_info(key)
        if not value:
            return []
        try:
            array = json.loads(value)
            return [str(item) for item in array]
        except (json.JSONDecodeError, TypeError):
            return []

    def append_ext_info_list(self, key: MandateExtendType, value: str) -> None:
        """
        Append a value to an extension info list.

        :param key: extension info key
        :param value: value to append
        """
        if not value:
            return
        existing = self.fetch_ext_info(key)
        if not existing:
            array: list = []
        else:
            try:
                array = json.loads(existing)
            except (json.JSONDecodeError, TypeError):
                array = []
        array.append(value)
        self.put_ext_info(key, json.dumps(array, ensure_ascii=False))

    def __repr__(self) -> str:
        return (
            f"Mandate(mandate_id={self.mandate_id!r}, token={self.token!r}, "
            f"mandate_type={self.mandate_type}, mandate_status={self.mandate_status}, "
            f"budget={self.budget}, gmt_create={self.gmt_create}, "
            f"gmt_modified={self.gmt_modified})"
        )


# ---------------------------------------------------------------------------
# Serialization helpers (shared with other schema models)
# ---------------------------------------------------------------------------


def dt_to_iso(dt: datetime | None) -> str | None:
    """Convert a datetime to ISO-8601 text, or None."""
    return dt.isoformat() if dt else None


def parse_dt_safe(value: str | None) -> datetime | None:
    """Parse ISO-8601 text back to a datetime, tolerant of common formats."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def money_to_dict(m: MultiCurrencyMoney | None) -> dict | None:
    """Serialize MultiCurrencyMoney to a plain dict."""
    if m is None:
        return None
    return {"cent": m.cent, "currency_code": m.currency_code}


def money_from_dict(d: dict | None) -> MultiCurrencyMoney | None:
    """Deserialize a plain dict back to MultiCurrencyMoney."""
    if d is None:
        return None
    return MultiCurrencyMoney.of(d["cent"], d["currency_code"])
