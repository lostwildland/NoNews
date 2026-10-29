from __future__ import annotations

def ensure_schema(db) -> None:
    db.execute("""CREATE TABLE IF NOT EXISTS literature_cleanup_media(
        request_id TEXT NOT NULL REFERENCES literature_cleanup_requests(id),
        object_key TEXT NOT NULL, public_url TEXT NOT NULL,
        sha256 TEXT NOT NULL, bytes INTEGER NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('pending','deleted','shared')),
        PRIMARY KEY(request_id,object_key))""")
    columns = {row[1] for row in db.execute("PRAGMA table_info(literature_cleanup_media)")}
    if "backup_path" in columns:
        # Old requests may have deleted remotely before receiving an ack while
        # the old writer still allowed a new direct reference. Keep only their
        # existing recovery anchor; new cleanup never creates a backup.
        db.execute("""CREATE TABLE IF NOT EXISTS literature_cleanup_legacy_media_recovery(
            request_id TEXT NOT NULL,object_key TEXT NOT NULL,path TEXT NOT NULL,
            PRIMARY KEY(request_id,object_key))""")
        db.execute("""INSERT OR IGNORE INTO literature_cleanup_legacy_media_recovery
            SELECT request_id,object_key,backup_path FROM literature_cleanup_media
            WHERE status='pending' AND backup_path<>''""")
        db.execute("ALTER TABLE literature_cleanup_media DROP COLUMN backup_path")
