from __future__ import annotations

SCHEMA = """
-- One row per item that has an exported reading note. ``item_id`` is the
-- identity; ``citekey``/``path`` are the frozen readable name and location of
-- the one note this flow created. ``body_version_id`` names the store version
-- the export read (NULL for a file-authority body), so a later background body
-- update is visible without ever rewriting the note.
CREATE TABLE IF NOT EXISTS literature_reading_notes(
 item_id TEXT PRIMARY KEY REFERENCES items(id),
 zotero_key TEXT NOT NULL DEFAULT '',
 citekey TEXT NOT NULL,
 path TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'exported'
   CHECK(status IN ('exported','missing')),
 payload_sha256 TEXT NOT NULL,
 body_version_id INTEGER,
 body_sha256 TEXT NOT NULL,
 fulltext_url TEXT NOT NULL DEFAULT '',
 extra_status TEXT NOT NULL DEFAULT 'pending'
   CHECK(extra_status IN ('pending','written','failed')),
 extra_error TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL);
"""

def ensure_schema(db) -> None:
    """Create the export mapping. Idempotent, run by the schema pass."""
    db.executescript(SCHEMA)
