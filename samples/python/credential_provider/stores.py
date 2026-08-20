"""Credential Provider — Local persistence for enrollment and mandate results.

CP stores tokens and mandates received via /notifyAuthorization callbacks.
This enables cross-session data lookup (e.g., queryPaymentMethodList returns
stored tokens, createMandateSession uses a previously stored token_id).

Data flow:
  - Initiate endpoints → write CpSessionModel (cp_session_id, status=PENDING_IDV)
  - ENROLLMENT callback → writes CpTokenModel (token_id, l1_serialized) + completes session
  - MANDATE callback → writes CpMandateModel (mandate_id, token_id, l2_serialized) + completes session
  - Query endpoints → read strictly by cp_session_id / token_id / mandate_id
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from common.sqlite_store import SqliteModel, SqliteRepo

logger = logging.getLogger("cp.store")

# ---------------------------------------------------------------------------
# SQLite database path (from environment variable)
# When empty, SqliteRepo uses a pure in-memory SQLite database.
# ---------------------------------------------------------------------------
CP_STORE_PATH: str = os.environ.get("CP_STORE_PATH", "")


def _now_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ===================================================================
# SQLite persistent model classes
# ===================================================================


class CpTokenModel(SqliteModel):
    """Enrollment token record stored locally by CP.

    Written when CP receives an ENROLLMENT /notifyAuthorization callback
    carrying token_id + l1_serialized + wallet_account_info.
    """

    def __init__(
        self,
        token_id: str = "",
        l1_serialized: str = "",
        session_id: str = "",
        customer_id: str = "",
        psp_id: str = "",
        wallet_name: str = "",
        wallet_account_info: str = "",
        gmt_create: str | None = None,
        gmt_modified: str | None = None,
    ) -> None:
        self.token_id = token_id
        self.l1_serialized = l1_serialized
        self.session_id = session_id
        self.customer_id = customer_id
        self.psp_id = psp_id
        self.wallet_name = wallet_name
        self.wallet_account_info = wallet_account_info
        self.gmt_create = gmt_create
        self.gmt_modified = gmt_modified

    @property
    def table_name(self) -> str:
        return "cp_token"

    @property
    def pk_column(self) -> str:
        return "token_id"

    @classmethod
    def columns(cls) -> list[tuple[str, str]]:
        return [
            ("token_id",            "TEXT PRIMARY KEY"),
            ("l1_serialized",       "TEXT"),
            ("session_id",          "TEXT"),
            ("customer_id",         "TEXT"),
            ("psp_id",              "TEXT"),
            ("wallet_name",         "TEXT"),
            ("wallet_account_info", "TEXT"),
            ("gmt_create",          "TEXT"),
            ("gmt_modified",        "TEXT"),
        ]

    def to_row(self) -> dict[str, Any]:
        return {
            "token_id":            self.token_id,
            "l1_serialized":       self.l1_serialized,
            "session_id":          self.session_id,
            "customer_id":         self.customer_id,
            "psp_id":              self.psp_id,
            "wallet_name":         self.wallet_name,
            "wallet_account_info": self.wallet_account_info,
            "gmt_create":          self.gmt_create,
            "gmt_modified":        self.gmt_modified,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> CpTokenModel:
        return cls(
            token_id=row.get("token_id") or "",
            l1_serialized=row.get("l1_serialized") or "",
            session_id=row.get("session_id") or "",
            customer_id=row.get("customer_id") or "",
            psp_id=row.get("psp_id") or "",
            wallet_name=row.get("wallet_name") or "",
            wallet_account_info=row.get("wallet_account_info") or "",
            gmt_create=row.get("gmt_create"),
            gmt_modified=row.get("gmt_modified"),
        )


class CpMandateModel(SqliteModel):
    """Mandate record stored locally by CP.

    Written when CP receives a MANDATE /notifyAuthorization callback
    carrying mandate_id + token_id + l2_serialized.
    """

    def __init__(
        self,
        mandate_id: str = "",
        token_id: str = "",
        l2_serialized: str = "",
        session_id: str = "",
        mandate_type: str = "",
        gmt_create: str | None = None,
        gmt_modified: str | None = None,
    ) -> None:
        self.mandate_id = mandate_id
        self.token_id = token_id
        self.l2_serialized = l2_serialized
        self.session_id = session_id
        self.mandate_type = mandate_type
        self.gmt_create = gmt_create
        self.gmt_modified = gmt_modified

    @property
    def table_name(self) -> str:
        return "cp_mandate"

    @property
    def pk_column(self) -> str:
        return "mandate_id"

    @classmethod
    def columns(cls) -> list[tuple[str, str]]:
        return [
            ("mandate_id",    "TEXT PRIMARY KEY"),
            ("token_id",      "TEXT"),
            ("l2_serialized", "TEXT"),
            ("session_id",    "TEXT"),
            ("mandate_type",  "TEXT"),
            ("gmt_create",    "TEXT"),
            ("gmt_modified",  "TEXT"),
        ]

    def to_row(self) -> dict[str, Any]:
        return {
            "mandate_id":    self.mandate_id,
            "token_id":      self.token_id,
            "l2_serialized": self.l2_serialized,
            "session_id":    self.session_id,
            "mandate_type":  self.mandate_type,
            "gmt_create":    self.gmt_create,
            "gmt_modified":  self.gmt_modified,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> CpMandateModel:
        return cls(
            mandate_id=row.get("mandate_id") or "",
            token_id=row.get("token_id") or "",
            l2_serialized=row.get("l2_serialized") or "",
            session_id=row.get("session_id") or "",
            mandate_type=row.get("mandate_type") or "",
            gmt_create=row.get("gmt_create"),
            gmt_modified=row.get("gmt_modified"),
        )


class CpSessionModel(SqliteModel):
    """CP-owned authorization session record.

    Created when CP accepts an initiate request (addPaymentMethod /
    createMandateSession). The CP-generated session_id is the contract key
    for all upstream follow-up calls; downstream_session_id keeps the
    mapping to the AlipayPlus session used for callback correlation.
    """

    def __init__(
        self,
        session_id: str = "",
        auth_context: str = "",
        status: str = "",
        downstream_session_id: str = "",
        auth_url: str = "",
        wallet_name: str = "",
        token_id: str = "",
        mandate_id: str = "",
        mandate_type: str = "",
        error: str = "",
        gmt_create: str | None = None,
        gmt_modified: str | None = None,
    ) -> None:
        self.session_id = session_id
        self.auth_context = auth_context
        self.status = status
        self.downstream_session_id = downstream_session_id
        self.auth_url = auth_url
        self.wallet_name = wallet_name
        self.token_id = token_id
        self.mandate_id = mandate_id
        self.mandate_type = mandate_type
        self.error = error
        self.gmt_create = gmt_create
        self.gmt_modified = gmt_modified

    @property
    def table_name(self) -> str:
        return "cp_session"

    @property
    def pk_column(self) -> str:
        return "session_id"

    @classmethod
    def columns(cls) -> list[tuple[str, str]]:
        return [
            ("session_id",            "TEXT PRIMARY KEY"),
            ("auth_context",          "TEXT"),  # ENROLLMENT | MANDATE
            ("status",                "TEXT"),  # PENDING_IDV | COMPLETED | FAILED
            ("downstream_session_id", "TEXT"),  # AlipayPlus session (callback key)
            ("auth_url",              "TEXT"),
            ("wallet_name",           "TEXT"),
            ("token_id",              "TEXT"),
            ("mandate_id",            "TEXT"),
            ("mandate_type",          "TEXT"),
            ("error",                 "TEXT"),
            ("gmt_create",            "TEXT"),
            ("gmt_modified",          "TEXT"),
        ]

    def to_row(self) -> dict[str, Any]:
        return {
            "session_id":            self.session_id,
            "auth_context":          self.auth_context,
            "status":                self.status,
            "downstream_session_id": self.downstream_session_id,
            "auth_url":              self.auth_url,
            "wallet_name":           self.wallet_name,
            "token_id":              self.token_id,
            "mandate_id":            self.mandate_id,
            "mandate_type":          self.mandate_type,
            "error":                 self.error,
            "gmt_create":            self.gmt_create,
            "gmt_modified":          self.gmt_modified,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> CpSessionModel:
        return cls(
            session_id=row.get("session_id") or "",
            auth_context=row.get("auth_context") or "",
            status=row.get("status") or "",
            downstream_session_id=row.get("downstream_session_id") or "",
            auth_url=row.get("auth_url") or "",
            wallet_name=row.get("wallet_name") or "",
            token_id=row.get("token_id") or "",
            mandate_id=row.get("mandate_id") or "",
            mandate_type=row.get("mandate_type") or "",
            error=row.get("error") or "",
            gmt_create=row.get("gmt_create"),
            gmt_modified=row.get("gmt_modified"),
        )


# ===================================================================
# CpStore — Unified facade for CP local persistence
# ===================================================================


class CpStore:
    """CP's local persistence — stores enrollment tokens and mandate credentials.

    Provides three logical collections:
      - Sessions: CP-owned authorization sessions (cp session_id + status)
      - Tokens: enrollment binding records (token_id + L1)
      - Mandates: mandate authorization records (mandate_id + token_id + L2)
    """

    def __init__(self) -> None:
        self._sessions: SqliteRepo[CpSessionModel] = SqliteRepo(CP_STORE_PATH, CpSessionModel)
        self._tokens: SqliteRepo[CpTokenModel] = SqliteRepo(CP_STORE_PATH, CpTokenModel)
        self._mandates: SqliteRepo[CpMandateModel] = SqliteRepo(CP_STORE_PATH, CpMandateModel)

    # ------------------------------------------------------------------
    # Session operations
    # ------------------------------------------------------------------

    def save_session(self, session_id: str, **kwargs: Any) -> None:
        """Persist a CP session record.

        Expected kwargs: auth_context, status, downstream_session_id,
        auth_url, wallet_name, token_id, mandate_id, mandate_type, error
        """
        now = _now_iso()
        existing = self._sessions.get(session_id)
        gmt_create = existing.gmt_create if existing else now
        self._sessions.save(CpSessionModel(
            session_id=session_id,
            auth_context=kwargs.get("auth_context", ""),
            status=kwargs.get("status", ""),
            downstream_session_id=kwargs.get("downstream_session_id", ""),
            auth_url=kwargs.get("auth_url", ""),
            wallet_name=kwargs.get("wallet_name", ""),
            token_id=kwargs.get("token_id", ""),
            mandate_id=kwargs.get("mandate_id", ""),
            mandate_type=kwargs.get("mandate_type", ""),
            error=kwargs.get("error", ""),
            gmt_create=gmt_create,
            gmt_modified=now,
        ))
        logger.debug("[CpStore] saved session %s (status=%s)", session_id, kwargs.get("status", ""))

    def update_session(self, session_id: str, **fields: Any) -> bool:
        """Merge fields into an existing session record. Returns False if absent."""
        existing = self._sessions.get(session_id)
        if existing is None:
            return False
        merged = existing.to_row()
        merged.update(fields)
        merged.pop("session_id", None)
        merged.pop("gmt_create", None)
        merged.pop("gmt_modified", None)
        self.save_session(session_id, **merged)
        return True

    def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        """Look up a session by CP session_id. Returns a flat dict or None."""
        model = self._sessions.get(session_id)
        if model is None:
            return None
        return model.to_row()

    def find_session_by_downstream_id(self, downstream_session_id: str) -> Optional[dict[str, Any]]:
        """Reverse lookup: AlipayPlus session_id → CP session record (callback path)."""
        model = self._sessions.find_by("downstream_session_id", downstream_session_id)
        if model is None:
            return None
        return model.to_row()

    # ------------------------------------------------------------------
    # Token operations
    # ------------------------------------------------------------------

    def save_token(self, token_id: str, **kwargs: Any) -> None:
        """Persist an enrollment token record.

        Expected kwargs: l1_serialized, session_id, customer_id, psp_id,
                         wallet_name, wallet_account_info (dict, stored as JSON)
        """
        now = _now_iso()
        existing = self._tokens.get(token_id)
        gmt_create = existing.gmt_create if existing else now
        # Serialize wallet_account_info dict to JSON string for storage
        wai = kwargs.get("wallet_account_info")
        wai_str = json.dumps(wai, ensure_ascii=False) if wai else ""
        self._tokens.save(CpTokenModel(
            token_id=token_id,
            l1_serialized=kwargs.get("l1_serialized", ""),
            session_id=kwargs.get("session_id", ""),
            customer_id=kwargs.get("customer_id", ""),
            psp_id=kwargs.get("psp_id", ""),
            wallet_name=kwargs.get("wallet_name", ""),
            wallet_account_info=wai_str,
            gmt_create=gmt_create,
            gmt_modified=now,
        ))
        logger.debug("[CpStore] saved token %s", token_id)

    def get_token(self, token_id: str) -> Optional[dict[str, Any]]:
        """Look up a token by ID. Returns a flat dict or None."""
        model = self._tokens.get(token_id)
        if model is None:
            return None
        return model.to_row()

    def list_tokens(self) -> list[dict[str, Any]]:
        """Return all stored token records as flat dicts."""
        return [m.to_row() for m in self._tokens.select_all()]

    # ------------------------------------------------------------------
    # Mandate operations
    # ------------------------------------------------------------------

    def save_mandate(self, mandate_id: str, **kwargs: Any) -> None:
        """Persist a mandate record.

        Expected kwargs: token_id, l2_serialized, session_id, mandate_type
        """
        now = _now_iso()
        existing = self._mandates.get(mandate_id)
        gmt_create = existing.gmt_create if existing else now
        self._mandates.save(CpMandateModel(
            mandate_id=mandate_id,
            token_id=kwargs.get("token_id", ""),
            l2_serialized=kwargs.get("l2_serialized", ""),
            session_id=kwargs.get("session_id", ""),
            mandate_type=kwargs.get("mandate_type", ""),
            gmt_create=gmt_create,
            gmt_modified=now,
        ))
        logger.debug("[CpStore] saved mandate %s", mandate_id)

    def get_mandate(self, mandate_id: str) -> Optional[dict[str, Any]]:
        """Look up a mandate by ID. Returns a flat dict or None."""
        model = self._mandates.get(mandate_id)
        if model is None:
            return None
        return model.to_row()

    def list_mandates(self) -> list[dict[str, Any]]:
        """Return all stored mandate records as flat dicts."""
        return [m.to_row() for m in self._mandates.select_all()]
