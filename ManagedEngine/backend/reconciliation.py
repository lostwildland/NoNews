from __future__ import annotations

def ensure_schema(db) -> None:
    """Create the reconciliation bookkeeping. Idempotent; run by the schema pass."""
    db.execute("""CREATE TABLE IF NOT EXISTS reconciliation_cursors (
        folder TEXT PRIMARY KEY, cursor TEXT, completed_at TEXT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS ingestion_failures (
        id TEXT PRIMARY KEY, folder TEXT NOT NULL, entry_id TEXT, artifact_path TEXT NOT NULL,
        error TEXT NOT NULL, updated_at TEXT NOT NULL, resolved INTEGER NOT NULL DEFAULT 0)""")
    db.execute("""CREATE TABLE IF NOT EXISTS reconciliation_bootstrap (
        feed_id TEXT PRIMARY KEY REFERENCES feeds(id),
        started_at TEXT NOT NULL,
        completed_at TEXT
    )""")
