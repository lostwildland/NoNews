from __future__ import annotations

import sqlite3

def ensure_schema(db: sqlite3.Connection) -> None:
    """Create media tables and top up recovery columns without a version bump."""
    db.execute("""CREATE TABLE IF NOT EXISTS media_objects(
        key TEXT PRIMARY KEY, namespace TEXT NOT NULL,
        sha256 TEXT NOT NULL, stored_sha256 TEXT NOT NULL, ext TEXT NOT NULL,
        bytes INTEGER NOT NULL, width INTEGER NOT NULL DEFAULT 0, height INTEGER NOT NULL DEFAULT 0,
        transcoded_from TEXT NOT NULL DEFAULT '', public_url TEXT NOT NULL,
        verified_at TEXT, created_at TEXT NOT NULL,
        UNIQUE(namespace, stored_sha256))""")
    object_columns = {row[1] for row in db.execute("PRAGMA table_info(media_objects)")}
    for name, definition in {
        "cleanup_generation": "INTEGER NOT NULL DEFAULT 0",
        "cleanup_request_id": "TEXT",
        "deleted_at": "TEXT",
    }.items():
        if name not in object_columns:
            db.execute(f"ALTER TABLE media_objects ADD COLUMN {name} {definition}")
    db.execute("""CREATE TABLE IF NOT EXISTS media_usages(
        object_key TEXT NOT NULL, owner_kind TEXT NOT NULL, owner_id TEXT NOT NULL,
        source_ref TEXT NOT NULL, first_seen_at TEXT NOT NULL,
        PRIMARY KEY(object_key, owner_kind, owner_id, source_ref))""")
    db.execute("""CREATE TABLE IF NOT EXISTS media_upload_intents(
        object_key TEXT NOT NULL, owner_kind TEXT NOT NULL, owner_id TEXT NOT NULL,
        source_ref TEXT NOT NULL, object_json TEXT NOT NULL, payload BLOB NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY(object_key,owner_kind,owner_id,source_ref))""")
    db.execute("CREATE INDEX IF NOT EXISTS media_upload_intents_owner ON media_upload_intents(owner_kind,owner_id)")
    db.execute("""CREATE TABLE IF NOT EXISTS media_pending(
        id INTEGER PRIMARY KEY,
        owner_kind TEXT NOT NULL, owner_id TEXT NOT NULL, source_ref TEXT NOT NULL,
        staging_path TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
        next_attempt_at TEXT, last_error TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
        UNIQUE(owner_kind, owner_id, source_ref))""")
    db.execute("""CREATE TABLE IF NOT EXISTS media_receipts(
        id INTEGER PRIMARY KEY,
        owner_kind TEXT NOT NULL, owner_id TEXT NOT NULL, raw_snapshot_id INTEGER,
        status TEXT NOT NULL, images_total INTEGER NOT NULL DEFAULT 0,
        uploaded INTEGER NOT NULL DEFAULT 0, reused INTEGER NOT NULL DEFAULT 0,
        skipped INTEGER NOT NULL DEFAULT 0, failed INTEGER NOT NULL DEFAULT 0,
        bytes_total INTEGER NOT NULL DEFAULT 0, detail_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL)""")
    columns = {row[1] for row in db.execute("PRAGMA table_info(media_pending)")}
    for name, definition in {
        "namespace": "TEXT NOT NULL DEFAULT 'literature'",
        "payload_sha256": "TEXT NOT NULL DEFAULT ''",
        "payload_bytes": "INTEGER NOT NULL DEFAULT 0",
        "staging_owned": "INTEGER NOT NULL DEFAULT 0",
        "staging_device": "INTEGER NOT NULL DEFAULT 0",
        "staging_inode": "INTEGER NOT NULL DEFAULT 0",
        "state": "TEXT NOT NULL DEFAULT 'pending'",
    }.items():
        if name not in columns:
            db.execute(f"ALTER TABLE media_pending ADD COLUMN {name} {definition}")
    db.execute("""CREATE TABLE IF NOT EXISTS media_source_current(
        namespace TEXT NOT NULL, owner_kind TEXT NOT NULL, owner_id TEXT NOT NULL,
        source_ref TEXT NOT NULL, object_key TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        PRIMARY KEY(namespace, owner_kind, owner_id, source_ref))""")
    db.execute("""CREATE TABLE IF NOT EXISTS media_source_revisions(
        namespace TEXT NOT NULL, owner_kind TEXT NOT NULL, owner_id TEXT NOT NULL,
        source_ref TEXT NOT NULL, source_revision TEXT NOT NULL, object_key TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        PRIMARY KEY(namespace, owner_kind, owner_id, source_ref, source_revision))""")
    db.execute("CREATE INDEX IF NOT EXISTS media_usages_owner ON media_usages(owner_kind, owner_id)")
