from __future__ import annotations

import sqlite3

SCHEMA = """
-- One row per (file, verified content) the migration imported. It carries the
-- evidence a reviewer needs -- original path, exact-bytes hash, content hash,
-- version, model, source association -- and nothing that could become a second
-- copy of the text. The primary key is derived from the identity and the content
-- hash, so re-running the same import updates one row instead of adding another.
-- ``version`` is the draft file's own vNNN (0 for a body, whose version identity
-- is ``target_id``: the archived snapshot the file was bound to). ``state`` is
-- always ``verified``: a file the migration cannot verify never gets a row.
CREATE TABLE IF NOT EXISTS legacy_content_imports(
 import_key TEXT PRIMARY KEY,
 batch TEXT NOT NULL DEFAULT '',
 item_id TEXT NOT NULL REFERENCES items(id),
 kind TEXT NOT NULL CHECK(kind IN ('body','draft')),
 path TEXT NOT NULL,
 file_sha256 TEXT NOT NULL,
 content_sha256 TEXT NOT NULL,
 version INTEGER NOT NULL DEFAULT 0,
 model TEXT NOT NULL DEFAULT '',
 source_system TEXT NOT NULL,
 source_key TEXT NOT NULL,
 source_hash TEXT NOT NULL DEFAULT '',
 target_id TEXT NOT NULL,
 state TEXT NOT NULL,
 verified_at TEXT NOT NULL,
 detail_json TEXT NOT NULL DEFAULT '{}');
CREATE INDEX IF NOT EXISTS legacy_content_imports_item
 ON legacy_content_imports(item_id, kind);
CREATE INDEX IF NOT EXISTS legacy_content_imports_target
 ON legacy_content_imports(target_id);
"""

def ensure_schema(db: sqlite3.Connection) -> None:
    """Create the migration ledger. Idempotent; run by the schema pass."""
    db.executescript(SCHEMA)
