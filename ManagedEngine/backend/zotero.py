from __future__ import annotations

def ensure_schema(db) -> None:
    """Create the Zotero resolution queue. Idempotent; run by the schema pass."""
    db.execute("""CREATE TABLE IF NOT EXISTS zotero_resolution(
        item_id TEXT PRIMARY KEY REFERENCES items(id), attempts INTEGER NOT NULL,
        status TEXT NOT NULL, available_at TEXT NOT NULL)""")
    columns = {row[1] for row in db.execute("PRAGMA table_info(zotero_links)")}
    for name in ("adoption_source", "adoption_status"):
        if name not in columns:
            db.execute(f"ALTER TABLE zotero_links ADD COLUMN {name} TEXT")
    if "sync_scope" not in columns:
        db.execute("ALTER TABLE zotero_links ADD COLUMN sync_scope TEXT NOT NULL DEFAULT 'parent-and-note'")
