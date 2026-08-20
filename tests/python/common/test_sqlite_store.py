"""SqliteStore functional tests — unittest, supports PyCharm breakpoint debugging"""
import sys
import os
import json
import shutil
import sqlite3
import unittest
from datetime import datetime, timezone

# Add src/python to sys.path (navigate up from tests/python/common/)
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(_project_root, "src", "python"))
sys.path.insert(0, os.path.join(_project_root, "samples", "python"))

from common.sqlite_store import SqliteStore, SqliteModel, SqliteRepo
from schemas.mandate import Mandate, MandateType, MandateStatus, Budget
from alipayplus.stores import MandateModel
from common.multi_currency_money import MultiCurrencyMoney

# Temp files are stored under tests/python/common/.temp-db/
_TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".temp-db")


# ── Mandate serialization helpers ─────────────────────────────────
def _mandate_to_dict(m: Mandate) -> dict:
    budget_d = None
    if m.budget:
        budget_d = {
            "total_cent": m.budget.total_budget_amount.cent if m.budget.total_budget_amount else None,
            "total_cur": m.budget.total_budget_amount.currency_code if m.budget.total_budget_amount else None,
            "used_cent": m.budget.used_amount.cent if m.budget.used_amount else None,
            "used_cur": m.budget.used_amount.currency_code if m.budget.used_amount else None,
            "rem_cent": m.budget.remaining_amount.cent if m.budget.remaining_amount else None,
            "rem_cur": m.budget.remaining_amount.currency_code if m.budget.remaining_amount else None,
        }
    return {
        "mandate_id": m.mandate_id,
        "mandate_type": m.mandate_type.value if m.mandate_type else None,
        "mandate_status": m.mandate_status.value if m.mandate_status else None,
        "budget": budget_d,
        "expiry_time": m.expiry_time.isoformat() if m.expiry_time else None,
    }


def _mandate_from_dict(d: dict) -> Mandate:
    m = Mandate()
    m.mandate_id = d.get("mandate_id")
    mt = d.get("mandate_type")
    m.mandate_type = MandateType(mt) if mt else None
    ms = d.get("mandate_status")
    m.mandate_status = MandateStatus(ms) if ms else None
    bd = d.get("budget")
    if bd:
        b = Budget()
        if bd.get("total_cent") is not None:
            b.total_budget_amount = MultiCurrencyMoney.of(bd["total_cent"], bd["total_cur"])
        if bd.get("used_cent") is not None:
            b.used_amount = MultiCurrencyMoney.of(bd["used_cent"], bd["used_cur"])
        if bd.get("rem_cent") is not None:
            b.remaining_amount = MultiCurrencyMoney.of(bd["rem_cent"], bd["rem_cur"])
        m.budget = b
    exp = d.get("expiry_time")
    m.expiry_time = datetime.fromisoformat(exp) if exp else None
    return m


# ── Test class ─────────────────────────────────────────────────────
class TestSqliteStore(unittest.TestCase):

    def setUp(self):
        # Clean up before each test to ensure isolation; files remain after run for inspection
        shutil.rmtree(_TEST_DIR, ignore_errors=True)
        os.makedirs(_TEST_DIR, exist_ok=True)

    def _path(self, name: str) -> str:
        return os.path.join(_TEST_DIR, name)

    # ── 1. In-memory mode ──
    def test_01_in_memory_mode(self):
        s = SqliteStore("")
        s.put("k1", {"v": 1})
        s.put("k2", [1, 2, 3])

        self.assertEqual(s.get("k1"), {"v": 1})
        self.assertEqual(s.get("k2"), [1, 2, 3])
        self.assertIsNone(s.get("no-key"))
        self.assertTrue(s.contains("k1"))
        self.assertFalse(s.contains("no-key"))
        self.assertEqual(sorted(s.keys()), ["k1", "k2"])

    # ── 2. File persistence mode ──
    def test_02_file_persistence(self):
        fp = self._path("store.db")
        s = SqliteStore(fp)
        s.put("t1", {"token_id": "t1", "data": "hello"})
        s.put("t2", {"token_id": "t2", "data": "world"})

        self.assertTrue(os.path.exists(fp))
        # Verify data directly in SQLite
        conn = sqlite3.connect(fp)
        cursor = conn.execute("SELECT key, value FROM store")
        rows = {row[0]: json.loads(row[1]) for row in cursor.fetchall()}
        conn.close()
        self.assertEqual(len(rows), 2)
        self.assertIn("t1", rows)
        self.assertIn("t2", rows)
        self.assertEqual(rows["t1"]["data"], "hello")

    # ── 3. Reload from file (simulate restart) ──
    def test_03_reload_from_file(self):
        fp = self._path("store.db")
        # Write first
        s = SqliteStore(fp)
        s.put("t1", {"token_id": "t1", "data": "hello"})
        s.put("t2", {"token_id": "t2", "data": "world"})

        # A new instance loads the same file
        s2 = SqliteStore(fp)
        self.assertEqual(s2.get("t1"), {"token_id": "t1", "data": "hello"})
        self.assertEqual(s2.get("t2"), {"token_id": "t2", "data": "world"})

    # ── 4. put_if_absent (idempotent write) ──
    def test_04_put_if_absent(self):
        fp = self._path("store.db")
        s = SqliteStore(fp)
        s.put("t1", {"token_id": "t1", "data": "hello"})

        r1 = s.put_if_absent("t1", {"token_id": "t1", "data": "OVERWRITTEN"})
        r2 = s.put_if_absent("t3", {"token_id": "t3", "data": "new"})

        self.assertFalse(r1)
        self.assertEqual(s.get("t1")["data"], "hello")  # value unchanged
        self.assertTrue(r2)
        self.assertEqual(s.get("t3")["data"], "new")

    # ── 5. remove ──
    def test_05_remove(self):
        fp = self._path("store.db")
        s = SqliteStore(fp)
        s.put("t3", {"token_id": "t3", "data": "new"})

        old = s.remove("t3")
        self.assertIsNotNone(old)
        self.assertEqual(old["data"], "new")
        self.assertIsNone(s.get("t3"))
        self.assertIsNone(s.remove("no-key"))

    # ── 6. snapshot ──
    def test_06_snapshot(self):
        fp = self._path("store.db")
        s = SqliteStore(fp)
        s.put("t1", {"token_id": "t1"})
        s.put("t2", {"token_id": "t2"})

        snap = s.snapshot()
        self.assertEqual(set(snap.keys()), {"t1", "t2"})

    # ── 7. Lock-based compound operations ──
    def test_07_lock_operations(self):
        fp = self._path("store.db")
        s = SqliteStore(fp)
        s.put("t1", {"token_id": "t1", "data": "hello"})

        s.acquire()
        v = s.get_locked("t1")
        self.assertIsNotNone(v)
        self.assertEqual(v["data"], "hello")

        v["data"] = "updated-via-lock"
        s.update_locked("t1", v)
        s.release()

        self.assertEqual(s.get("t1")["data"], "updated-via-lock")

        # Verify persistence
        s2 = SqliteStore(fp)
        self.assertEqual(s2.get("t1")["data"], "updated-via-lock")

    # ── 8. Custom serialization / deserialization (Mandate domain object) ──
    def test_08_mandate_serialization(self):
        fp = self._path("mandate_store.db")
        store = SqliteStore(fp, serializer=_mandate_to_dict, deserializer=_mandate_from_dict)

        m = Mandate()
        m.mandate_id = "md-001"
        m.mandate_type = MandateType.AUTONOMOUS
        m.mandate_status = MandateStatus.ACTIVE
        m.budget = Budget()
        m.budget.total_budget_amount = MultiCurrencyMoney.of(10000, "USD")
        m.budget.used_amount = MultiCurrencyMoney.of(0, "USD")
        m.budget.remaining_amount = MultiCurrencyMoney.of(10000, "USD")
        m.expiry_time = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        store.put("md-001", m)
        self.assertTrue(os.path.exists(fp))

        # Verify raw data directly in SQLite
        conn = sqlite3.connect(fp)
        cursor = conn.execute("SELECT value FROM store WHERE key = ?", ("md-001",))
        raw = json.loads(cursor.fetchone()[0])
        conn.close()
        self.assertEqual(raw["mandate_type"], "AUTONOMOUS")
        self.assertEqual(raw["budget"]["total_cent"], 10000)

        # New instance loads and deserializes back
        store2 = SqliteStore(fp, serializer=_mandate_to_dict, deserializer=_mandate_from_dict)
        m2 = store2.get("md-001")
        self.assertEqual(m2.mandate_id, "md-001")
        self.assertEqual(m2.mandate_type, MandateType.AUTONOMOUS)
        self.assertEqual(m2.mandate_status, MandateStatus.ACTIVE)
        self.assertEqual(m2.budget.total_budget_amount.cent, 10000)
        self.assertEqual(m2.budget.total_budget_amount.currency_code, "USD")
        self.assertEqual(m2.budget.remaining_amount.cent, 10000)
        self.assertEqual(m2.expiry_time.year, 2026)
        self.assertEqual(m2.expiry_time.month, 12)

    # ── 9. Missing DB file (tolerant startup) ──
    def test_09_missing_db_file(self):
        s_empty = SqliteStore(self._path("non_existent.db"))
        self.assertEqual(s_empty.keys(), [])


# ── Test class for SqliteRepo ────────────────────────────────────
class TestSqliteRepo(unittest.TestCase):

    def setUp(self):
        shutil.rmtree(_TEST_DIR, ignore_errors=True)
        os.makedirs(_TEST_DIR, exist_ok=True)

    def _path(self, name: str) -> str:
        return os.path.join(_TEST_DIR, name)

    def _make_mandate(self, mid: str, mtype=MandateType.AUTONOMOUS,
                      status=MandateStatus.ACTIVE, cent=10000) -> MandateModel:
        m = MandateModel()
        m.mandate_id = mid
        m.token = f"tok-{mid}"
        m.mandate_type = mtype
        m.mandate_status = status
        m.budget = Budget()
        m.budget.total_budget_amount = MultiCurrencyMoney.of(cent, "USD")
        m.budget.used_amount = MultiCurrencyMoney.of(0, "USD")
        m.expiry_time = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        return m

    # ── 1. In-memory SqliteRepo ──
    def test_01_in_memory_repo(self):
        repo = SqliteRepo("", MandateModel)
        m = self._make_mandate("md-001")
        repo.save(m)
        got = repo.get("md-001")
        self.assertIsNotNone(got)
        self.assertEqual(got.mandate_id, "md-001")
        self.assertEqual(got.mandate_type, MandateType.AUTONOMOUS)
        self.assertEqual(got.budget.total_budget_amount.cent, 10000)

    # ── 2. File persistence with typed columns ──
    def test_02_file_persistence(self):
        fp = self._path("mandate.db")
        repo = SqliteRepo(fp, MandateModel)
        m = self._make_mandate("md-002")
        repo.save(m)

        # Verify the table schema and data directly in SQLite
        conn = sqlite3.connect(fp)
        cursor = conn.execute("PRAGMA table_info(mandate)")
        col_names = [row[1] for row in cursor.fetchall()]
        conn.close()
        self.assertIn("mandate_id", col_names)
        self.assertIn("mandate_type", col_names)
        self.assertIn("budget", col_names)

    # ── 3. Reload from file ──
    def test_03_reload_from_file(self):
        fp = self._path("mandate.db")
        repo = SqliteRepo(fp, MandateModel)
        repo.save(self._make_mandate("md-003"))

        repo2 = SqliteRepo(fp, MandateModel)
        got = repo2.get("md-003")
        self.assertIsNotNone(got)
        self.assertEqual(got.mandate_status, MandateStatus.ACTIVE)
        self.assertEqual(got.expiry_time.year, 2026)

    # ── 4. save_if_absent (idempotent) ──
    def test_04_save_if_absent(self):
        repo = SqliteRepo("", MandateModel)
        m1 = self._make_mandate("md-004")
        m2 = self._make_mandate("md-004", cent=99999)
        self.assertTrue(repo.save_if_absent(m1))
        self.assertFalse(repo.save_if_absent(m2))
        got = repo.get("md-004")
        self.assertEqual(got.budget.total_budget_amount.cent, 10000)  # original value

    # ── 5. delete and contains ──
    def test_05_delete_and_contains(self):
        repo = SqliteRepo("", MandateModel)
        repo.save(self._make_mandate("md-005"))
        self.assertTrue(repo.contains("md-005"))
        self.assertTrue(repo.delete("md-005"))
        self.assertFalse(repo.contains("md-005"))
        self.assertIsNone(repo.get("md-005"))
        self.assertFalse(repo.delete("nonexistent"))

    # ── 6. select_all ──
    def test_06_select_all(self):
        repo = SqliteRepo("", MandateModel)
        repo.save(self._make_mandate("md-a"))
        repo.save(self._make_mandate("md-b"))
        repo.save(self._make_mandate("md-c"))
        all_items = repo.select_all()
        self.assertEqual(len(all_items), 3)
        ids = {m.mandate_id for m in all_items}
        self.assertEqual(ids, {"md-a", "md-b", "md-c"})

    # ── 7. Lock-based compound operations ──
    def test_07_lock_operations(self):
        fp = self._path("mandate.db")
        repo = SqliteRepo(fp, MandateModel)
        m = self._make_mandate("md-007")
        repo.save(m)

        repo.acquire()
        locked = repo.get_locked("md-007")
        self.assertIsNotNone(locked)
        locked.mandate_status = MandateStatus.REVOKED
        repo.save_locked(locked)
        repo.release()

        got = repo.get("md-007")
        self.assertEqual(got.mandate_status, MandateStatus.REVOKED)

        # Verify persistence
        repo2 = SqliteRepo(fp, MandateModel)
        got2 = repo2.get("md-007")
        self.assertEqual(got2.mandate_status, MandateStatus.REVOKED)

    # ── 8. Overwrite (save replaces existing) ──
    def test_08_overwrite(self):
        repo = SqliteRepo("", MandateModel)
        m = self._make_mandate("md-008", status=MandateStatus.ACTIVE)
        repo.save(m)
        m.mandate_status = MandateStatus.CLOSED
        repo.save(m)
        got = repo.get("md-008")
        self.assertEqual(got.mandate_status, MandateStatus.CLOSED)
        self.assertEqual(len(repo.select_all()), 1)

    # ── 9. find_by (non-PK column lookup) ──
    def test_09_find_by(self):
        repo = SqliteRepo("", MandateModel)
        m1 = self._make_mandate("md-009a")
        m1.token = "shared-token"
        m2 = self._make_mandate("md-009b")
        m2.token = "shared-token"
        m3 = self._make_mandate("md-009c")
        m3.token = "other-token"
        repo.save(m1)
        repo.save(m2)
        repo.save(m3)

        # find_by returns the first match (not all)
        found = repo.find_by("token", "shared-token")
        self.assertIsNotNone(found)
        self.assertIn(found.mandate_id, {"md-009a", "md-009b"})

        # Non-existent value returns None
        self.assertIsNone(repo.find_by("token", "nonexistent"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
