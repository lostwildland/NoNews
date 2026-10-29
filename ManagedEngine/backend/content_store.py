from __future__ import annotations

import sqlite3

SCHEMA = """
-- One row per archived Raw snapshot that the database holds the text of. The
-- snapshot itself stays the provenance row (source hash, retrieval time); this
-- row adds what only the store can attest: the exact bytes' hash, the source
-- identity in readable form, and usability. No text: see ``body_texts``.
CREATE TABLE IF NOT EXISTS body_versions(
 snapshot_id INTEGER PRIMARY KEY REFERENCES raw_snapshots(id),
 item_id TEXT NOT NULL REFERENCES items(id),
 sha256 TEXT NOT NULL,
 characters INTEGER NOT NULL,
 format TEXT NOT NULL DEFAULT 'markdown',
 authority TEXT NOT NULL DEFAULT 'database'
   CHECK(authority IN ('database','imported')),
 source TEXT NOT NULL,
 source_url TEXT NOT NULL DEFAULT '',
 availability TEXT NOT NULL DEFAULT 'usable'
   CHECK(availability IN ('usable','unavailable')),
 availability_reason TEXT NOT NULL DEFAULT '',
 retrieved_at TEXT NOT NULL,
 stored_at TEXT NOT NULL,
 cleaned_at TEXT, cleanup_request_id TEXT);
CREATE INDEX IF NOT EXISTS body_versions_item ON body_versions(item_id, snapshot_id);
CREATE TABLE IF NOT EXISTS body_texts(
 snapshot_id INTEGER PRIMARY KEY REFERENCES body_versions(snapshot_id),
 text TEXT NOT NULL);
-- One row per AI draft version the database holds the text of. The draft's
-- model, prompt, input hash and input body version stay in ``editor_drafts``:
-- this row adds the text identity and size, so a version list needs no text.
CREATE TABLE IF NOT EXISTS draft_versions(
 draft_id TEXT PRIMARY KEY REFERENCES editor_drafts(id),
 item_id TEXT NOT NULL REFERENCES items(id),
 sha256 TEXT NOT NULL,
 characters INTEGER NOT NULL,
 authority TEXT NOT NULL DEFAULT 'database'
   CHECK(authority IN ('database','imported')),
 stored_at TEXT NOT NULL,
 cleaned_at TEXT, cleanup_request_id TEXT);
CREATE INDEX IF NOT EXISTS draft_versions_item ON draft_versions(item_id, draft_id);
CREATE TABLE IF NOT EXISTS draft_bodies(
 draft_id TEXT PRIMARY KEY REFERENCES draft_versions(draft_id),
 text TEXT NOT NULL);
"""

_ADDED_COLUMNS = {
    "body_versions": (("authority", "TEXT NOT NULL DEFAULT 'database' "
                                     "CHECK(authority IN ('database','imported'))"),
                      # A Reject cleanup removes the text but keeps this row as a
                      # version tombstone: identity, source, hash, size and the
                      # request that cleared it remain readable.
                      ("cleaned_at", "TEXT"), ("cleanup_request_id", "TEXT")),
    "draft_versions": (("authority", "TEXT NOT NULL DEFAULT 'database' "
                                      "CHECK(authority IN ('database','imported'))"),
                       ("cleaned_at", "TEXT"), ("cleanup_request_id", "TEXT")),
}

def ensure_schema(db: sqlite3.Connection) -> None:
    """Create the store's tables. Idempotent; run by the schema pass."""
    db.executescript(SCHEMA)
    for table, columns in _ADDED_COLUMNS.items():
        existing = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
        for name, definition in columns:
            if name not in existing:
                db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
