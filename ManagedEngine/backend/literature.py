from __future__ import annotations

def ensure_schema(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS literature_assets (
            id INTEGER PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id),
            kind TEXT NOT NULL, source_path TEXT NOT NULL, archive_path TEXT,
            source_url TEXT, file_hash TEXT NOT NULL,
            identity_verified INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            UNIQUE(item_id,kind,source_path,file_hash)
        );
        CREATE INDEX IF NOT EXISTS literature_assets_item ON literature_assets(item_id,kind);
    """)
