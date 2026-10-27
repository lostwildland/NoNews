from __future__ import annotations

from . import reject_media_cleanup

import sqlite3

SCHEMA = """
-- Explicit maintenance operations and historical cleanup backups share this
-- ledger. Daily Reject cleanup never writes payload backups.
CREATE TABLE IF NOT EXISTS literature_cleanup_backups(
 backup_id TEXT PRIMARY KEY,
 request_id TEXT NOT NULL,
 item_id TEXT NOT NULL REFERENCES items(id),
 path TEXT NOT NULL,
 manifest_sha256 TEXT NOT NULL,
 bytes INTEGER NOT NULL,
 body_count INTEGER NOT NULL,
 draft_count INTEGER NOT NULL,
 verified_at TEXT NOT NULL,
 created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS literature_cleanup_backups_request
 ON literature_cleanup_backups(request_id);
-- Append-only record of what the cleanup owner decided and did. A request row
-- carries current state; these rows keep the history (held, backup, executed,
-- failed) that an audit needs even after the state moves on.
CREATE TABLE IF NOT EXISTS literature_cleanup_audit(
 id INTEGER PRIMARY KEY,
 request_id TEXT NOT NULL,
 item_id TEXT NOT NULL REFERENCES items(id),
 event TEXT NOT NULL,
 detail_json TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS literature_cleanup_audit_request
 ON literature_cleanup_audit(request_id, id);
"""

def ensure_schema(db: sqlite3.Connection) -> None:
    """Create the backup ledger and audit table. Idempotent; schema pass."""
    db.executescript(SCHEMA)
    reject_media_cleanup.ensure_schema(db)
