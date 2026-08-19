"""
SQLite persistence layer — two complementary abstractions:

1. **SqliteStore** — Generic KV store (key TEXT, value TEXT as JSON).
   Ideal for ad-hoc dict storage (sessions, tokens, etc.).

2. **SqliteModel + SqliteRepo[T]** — Schema-aware typed repository.
   Each model declares its table name, primary key, column definitions,
   and row conversion logic. SqliteRepo[T] provides typed CRUD with
   compound lock support.

Typical usage
-------------
    # --- KV store (plain dicts) ---
    store = SqliteStore(os.environ.get("SESSION_STORE_PATH", ""))
    store.put("sess-1", {"session_type": "ENROLLMENT", "status": "CREATED"})

    # --- Typed model + repository ---
    class MandateModel(Mandate, SqliteModel):
        @property
        def table_name(self) -> str: return "mandate"
        @property
        def pk_column(self) -> str: return "mandate_id"
        @classmethod
        def columns(cls) -> list[tuple[str, str]]:
            return [
                ("mandate_id", "TEXT PRIMARY KEY"),
                ("token", "TEXT"),
                ...
            ]
        def to_row(self) -> dict[str, Any]: ...
        @classmethod
        def from_row(cls, row: dict[str, Any]) -> "MandateModel": ...

    repo = SqliteRepo[MandateModel]("/path/to/store.db", MandateModel)
    repo.save(mandate_model)
    m = repo.get("md-001")
"""

from __future__ import annotations

import copy
import json
import logging
import sqlite3
import threading
from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, Optional, TypeVar

logger = logging.getLogger(__name__)

V = TypeVar("V")
R = TypeVar("R")

# Serializer / deserializer function signatures
Serializer = Callable[[Any], Any]       # domain object  -> JSON-compatible dict
Deserializer = Callable[[Any], Any]     # JSON-compatible dict -> domain object

_CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS store (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
"""


class SqliteStore:
    """Thread-safe KV store backed by a SQLite database.

    Parameters
    ----------
    path : str
        Path to the SQLite database file. Empty string or None uses an
        in-memory SQLite database (no file I/O, data lost on process exit).
    serializer : callable, optional
        Converts a value object into a JSON-compatible dict.
        Defaults to None (value is already JSON-compatible).
    deserializer : callable, optional
        Converts a JSON dict back into a value object.
        Defaults to None (returns the raw JSON dict as-is).
    """

    def __init__(
            self,
            path: str = "",
            *,
            serializer: Serializer | None = None,
            deserializer: Deserializer | None = None,
    ) -> None:
        self._path: str = path or ""
        self._serializer = serializer
        self._deserializer = deserializer
        self._lock = threading.Lock()
        # Connect to SQLite; ":memory:" when no path given
        db_uri = self._path if self._path else ":memory:"
        self._conn = sqlite3.connect(db_uri, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(_CREATE_TABLE_SQL)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Any | None:
        """Look up by key, returns a deep copy. Returns None if not found."""
        with self._lock:
            return self._get_impl(key)

    def put(self, key: str, value: Any) -> None:
        """Insert or overwrite a key-value pair and persist to DB."""
        with self._lock:
            self._put_impl(key, value)

    def put_if_absent(self, key: str, value: Any) -> bool:
        """Insert only if key is absent. Returns True if written, False otherwise."""
        with self._lock:
            existing = self._get_raw(key)
            if existing is not None:
                return False
            self._put_impl(key, value)
            return True

    def remove(self, key: str) -> Any | None:
        """Delete and return the old value. Returns None if not found."""
        with self._lock:
            old = self._get_impl(key)
            if old is not None:
                self._conn.execute("DELETE FROM store WHERE key = ?", (key,))
                self._conn.commit()
            return old

    def contains(self, key: str) -> bool:
        with self._lock:
            return self._get_raw(key) is not None

    def keys(self) -> list[str]:
        with self._lock:
            cursor = self._conn.execute("SELECT key FROM store")
            return [row[0] for row in cursor.fetchall()]

    def snapshot(self) -> dict[str, Any]:
        """Return a deep copy of the entire store (for debugging / logging)."""
        with self._lock:
            result: dict[str, Any] = {}
            cursor = self._conn.execute("SELECT key, value FROM store")
            for key, raw_value in cursor.fetchall():
                result[key] = copy.deepcopy(self._deserialize(json.loads(raw_value)))
            return result

    # ------------------------------------------------------------------
    # Lock-based compound operation support
    # ------------------------------------------------------------------

    def acquire(self) -> None:
        """Acquire the lock manually for lock -> mutate -> update -> release patterns."""
        self._lock.acquire()

    def release(self) -> None:
        """Release the manually acquired lock."""
        try:
            self._lock.release()
        except RuntimeError:
            pass

    def get_locked(self, key: str) -> Any | None:
        """Read under an already-held lock (no re-lock to avoid deadlock). Returns a deep copy."""
        return self._get_impl(key)

    def update_locked(self, key: str, value: Any) -> None:
        """Write back under an already-held lock and persist."""
        self._put_impl(key, value)

    # ------------------------------------------------------------------
    # Internal: DB I/O (caller must hold self._lock)
    # ------------------------------------------------------------------

    def _get_raw(self, key: str) -> str | None:
        """Return raw JSON text for key, or None if absent."""
        cursor = self._conn.execute("SELECT value FROM store WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else None

    def _get_impl(self, key: str) -> Any | None:
        """Deserialize and return a deep copy of the value for key."""
        raw = self._get_raw(key)
        if raw is None:
            return None
        try:
            value = self._deserialize(json.loads(raw))
            return copy.deepcopy(value)
        except Exception:
            logger.warning("[SqliteStore] skip corrupt record: %s in %s", key, self._path)
            return None

    def _put_impl(self, key: str, value: Any) -> None:
        """Serialize and upsert a key-value pair."""
        serialized = self._serialize(copy.deepcopy(value))
        raw_value = json.dumps(serialized, ensure_ascii=False, default=str)
        self._conn.execute(
            "INSERT OR REPLACE INTO store (key, value) VALUES (?, ?)",
            (key, raw_value),
        )
        self._conn.commit()

    def _serialize(self, value: Any) -> Any:
        if self._serializer is not None:
            return self._serializer(value)
        return value

    def _deserialize(self, raw: Any) -> Any:
        if self._deserializer is not None:
            return self._deserializer(raw)
        return raw


# ===================================================================
# SqliteModel — Base class for typed persistent models
# ===================================================================

T = TypeVar("T", bound="SqliteModel")


class SqliteModel(ABC):
    """Base class for SQLite-persisted domain models with explicit column schema.

    Subclasses declare:
      - ``table_name``  — SQL table name
      - ``pk_column``   — primary key column name (must match a column in ``columns()``)
      - ``columns()``   — ordered list of ``(column_name, sql_type)`` tuples
      - ``to_row()``    — convert model instance to a dict of column values
      - ``from_row()``  — reconstruct a model instance from a column-value dict

    Example
    -------
        class MandateModel(Mandate, SqliteModel):
            @property
            def table_name(self): return "mandate"
            @property
            def pk_column(self): return "mandate_id"
            @classmethod
            def columns(cls):
                return [
                    ("mandate_id", "TEXT PRIMARY KEY"),
                    ("token", "TEXT"),
                    ("mandate_type", "TEXT"),
                    ...
                ]
            def to_row(self) -> dict[str, Any]: ...
            @classmethod
            def from_row(cls, row: dict[str, Any]) -> "MandateModel": ...
    """

    @property
    @abstractmethod
    def table_name(self) -> str:
        """SQL table name for this model."""
        ...

    @property
    @abstractmethod
    def pk_column(self) -> str:
        """Primary key column name."""
        ...

    @classmethod
    @abstractmethod
    def columns(cls) -> list[tuple[str, str]]:
        """Column definitions as ``(name, sql_type_declaration)`` pairs.

        The first entry should be the primary key, e.g.
        ``("mandate_id", "TEXT PRIMARY KEY")``.
        """
        ...

    @abstractmethod
    def to_row(self) -> dict[str, Any]:
        """Convert this model instance to a dict mapping column names to values.

        Values must be SQLite-compatible: str, int, float, None, or bytes.
        Use ``json.dumps(...)`` for complex nested objects.
        """
        ...

    @classmethod
    @abstractmethod
    def from_row(cls: type[T], row: dict[str, Any]) -> T:
        """Reconstruct a model instance from a dict of column values.

        The dict keys match ``columns()``, values are raw SQLite types.
        """
        ...

    @property
    def pk_value(self) -> str:
        """Primary key value extracted from this instance via ``to_row()``."""
        return str(self.to_row()[self.pk_column])

    def create_table_sql(self) -> str:
        """Generate the CREATE TABLE IF NOT EXISTS statement."""
        cols = ", ".join(f"{name} {decl}" for name, decl in self.columns())
        return f"CREATE TABLE IF NOT EXISTS {self.table_name} ({cols})"


# ===================================================================
# SqliteRepo[T] — Generic typed repository for SqliteModel subclasses
# ===================================================================


class SqliteRepo(Generic[T]):
    """Thread-safe typed repository backed by a SQLite table.

    Each ``SqliteRepo`` manages exactly one table, defined by the model
    class passed at construction time.  It provides:

    - **save / save_if_absent** — insert or upsert
    - **get** — lookup by primary key
    - **delete / contains** — remove or test existence
    - **select_all** — full table scan
    - **Compound lock support** — ``acquire / get_locked / save_locked / release``
      for read-modify-write patterns that must be atomic.

    Parameters
    ----------
    path : str
        Path to the SQLite database file. Empty string uses ``:memory:``.
    model_cls : type[T]
        The ``SqliteModel`` subclass that defines the table schema and
        row conversion logic.
    """

    def __init__(self, path: str, model_cls: type[T]) -> None:
        self._model_cls = model_cls
        self._lock = threading.Lock()
        db_uri = path if path else ":memory:"
        self._conn = sqlite3.connect(db_uri, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(model_cls().create_table_sql())
        self._sync_columns()
        self._conn.commit()

    def _sync_columns(self) -> None:
        """Add any columns declared in the model that are missing from the existing table.

        This handles the case where the database file was created with an older
        schema and the model has since been extended with new columns.
        ``CREATE TABLE IF NOT EXISTS`` silently skips when the table already
        exists, so we explicitly ``ALTER TABLE ADD COLUMN`` for each gap.
        """
        m = self._model_cls()
        cursor = self._conn.execute(f"PRAGMA table_info({m.table_name})")
        existing_cols = {row[1] for row in cursor.fetchall()}
        for col_name, col_decl in m.columns():
            if col_name not in existing_cols:
                # col_decl is e.g. "TEXT PRIMARY KEY" — take only the type keyword
                col_type = col_decl.split()[0] if col_decl else "TEXT"
                try:
                    self._conn.execute(
                        f"ALTER TABLE {m.table_name} ADD COLUMN {col_name} {col_type}"
                    )
                    logger.info(
                        "[SqliteRepo] added missing column %s.%s (%s)",
                        m.table_name, col_name, col_type,
                    )
                except Exception:
                    logger.warning(
                        "[SqliteRepo] failed to add column %s.%s",
                        m.table_name, col_name, exc_info=True,
                    )

    # ------------------------------------------------------------------
    # Public CRUD API
    # ------------------------------------------------------------------

    def save(self, model: T) -> None:
        """Insert or replace a model instance."""
        with self._lock:
            self._save_impl(model)

    def save_if_absent(self, model: T) -> bool:
        """Insert only if the primary key does not exist. Returns True if written."""
        with self._lock:
            pk = model.pk_value
            row = self._conn.execute(
                f"SELECT 1 FROM {model.table_name} WHERE {model.pk_column} = ?", (pk,)
            ).fetchone()
            if row:
                return False
            self._save_impl(model)
            return True

    def get(self, pk: str) -> T | None:
        """Look up by primary key. Returns a fresh instance (deep copy), or None."""
        with self._lock:
            return self._get_impl(pk)

    def delete(self, pk: str) -> bool:
        """Delete by primary key. Returns True if a row was removed."""
        with self._lock:
            cursor = self._conn.execute(
                f"DELETE FROM {self._model_cls().table_name} WHERE {self._model_cls().pk_column} = ?",
                (pk,),
            )
            self._conn.commit()
            return cursor.rowcount > 0

    def contains(self, pk: str) -> bool:
        with self._lock:
            m = self._model_cls()
            row = self._conn.execute(
                f"SELECT 1 FROM {m.table_name} WHERE {m.pk_column} = ?", (pk,)
            ).fetchone()
            return row is not None

    def select_all(self) -> list[T]:
        """Return all rows as model instances."""
        with self._lock:
            m = self._model_cls()
            cursor = self._conn.execute(f"SELECT * FROM {m.table_name}")
            return [self._model_cls.from_row(dict(r)) for r in cursor.fetchall()]

    def find_by(self, column: str, value: Any) -> T | None:
        """Look up the first row matching *column = value*. Returns None if not found."""
        with self._lock:
            m = self._model_cls()
            cursor = self._conn.execute(
                f"SELECT * FROM {m.table_name} WHERE {column} = ?", (value,)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._model_cls.from_row(dict(row))

    # ------------------------------------------------------------------
    # Lock-based compound operation support
    # ------------------------------------------------------------------

    def acquire(self) -> None:
        """Acquire the lock for lock → read → mutate → save → release patterns."""
        self._lock.acquire()

    def release(self) -> None:
        """Release the manually acquired lock."""
        try:
            self._lock.release()
        except RuntimeError:
            pass

    def get_locked(self, pk: str) -> T | None:
        """Read under an already-held lock (no re-lock)."""
        return self._get_impl(pk)

    def save_locked(self, model: T) -> None:
        """Save under an already-held lock."""
        self._save_impl(model)

    # ------------------------------------------------------------------
    # Internal (caller must hold self._lock)
    # ------------------------------------------------------------------

    def _save_impl(self, model: T) -> None:
        row = model.to_row()
        cols = ", ".join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        self._conn.execute(
            f"INSERT OR REPLACE INTO {model.table_name} ({cols}) VALUES ({placeholders})",
            list(row.values()),
        )
        self._conn.commit()

    def _get_impl(self, pk: str) -> T | None:
        m = self._model_cls()
        cursor = self._conn.execute(
            f"SELECT * FROM {m.table_name} WHERE {m.pk_column} = ?", (pk,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._model_cls.from_row(dict(row))
