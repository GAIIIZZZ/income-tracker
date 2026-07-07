import json
import sqlite3
from contextlib import contextmanager

from .config import DB_PATH, ZONE_PROFILES_SEED_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    is_favorite INTEGER NOT NULL DEFAULT 0,
    batch_type TEXT NOT NULL DEFAULT 'income',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER REFERENCES batches(id) ON DELETE CASCADE,
    draft_slot INTEGER DEFAULT 1,
    transaction_type TEXT NOT NULL DEFAULT 'income',
    source_image_path TEXT,
    processed_image_path TEXT,
    sender_name TEXT,
    transaction_date TEXT,
    transaction_time TEXT,
    amount REAL,
    notes TEXT,
    raw_ocr_text TEXT,
    llm_raw_response TEXT,
    confidence REAL,
    status TEXT NOT NULL DEFAULT 'pending',
    recheck_status TEXT,
    recheck_note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    field TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS zone_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    identifier_keywords TEXT NOT NULL DEFAULT '',
    image_hash TEXT,
    sample_image_path TEXT,
    zones_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# Columns added after the initial release. Safe to re-run: duplicate-column errors are ignored
# so existing databases (with real data) get upgraded in place instead of being recreated.
MIGRATIONS = [
    "ALTER TABLE transactions ADD COLUMN draft_slot INTEGER DEFAULT 1",
    "ALTER TABLE batches ADD COLUMN is_favorite INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE zone_profiles ADD COLUMN image_hash TEXT",
    "ALTER TABLE transactions ADD COLUMN transaction_type TEXT NOT NULL DEFAULT 'income'",
    "ALTER TABLE batches ADD COLUMN batch_type TEXT NOT NULL DEFAULT 'income'",
]


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        for stmt in MIGRATIONS:
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError:
                pass  # column already exists
        _seed_zone_profiles_if_empty(conn)
        _backfill_zone_profile_hashes(conn)


def _seed_zone_profiles_if_empty(conn) -> None:
    if not ZONE_PROFILES_SEED_PATH.exists():
        return
    count = conn.execute("SELECT COUNT(*) as c FROM zone_profiles").fetchone()["c"]
    if count > 0:
        return
    try:
        from .pipeline import zone_seed
        data = json.loads(ZONE_PROFILES_SEED_PATH.read_text(encoding="utf-8"))
        imported = zone_seed.import_profiles(conn, data)
        if imported:
            print(f"[db] Seeded {imported} default zone profile(s) from {ZONE_PROFILES_SEED_PATH.name}")
    except Exception as exc:
        print(f"[db] Failed to seed zone profiles from {ZONE_PROFILES_SEED_PATH.name}: {exc}")


def _backfill_zone_profile_hashes(conn) -> None:
    """Profiles created before visual matching existed have a sample image but no hash yet —
    compute it once so they become matchable without needing to be recalibrated."""
    rows = conn.execute(
        "SELECT id, sample_image_path FROM zone_profiles WHERE image_hash IS NULL AND sample_image_path IS NOT NULL"
    ).fetchall()
    if not rows:
        return
    from .pipeline import zonal
    updated = 0
    for row in rows:
        try:
            image_hash = zonal.compute_image_hash(row["sample_image_path"])
            conn.execute("UPDATE zone_profiles SET image_hash = ? WHERE id = ?", (image_hash, row["id"]))
            updated += 1
        except Exception as exc:
            print(f"[db] Could not compute image hash for zone profile {row['id']}: {exc}")
    if updated:
        print(f"[db] Backfilled image hash for {updated} existing zone profile(s)")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
