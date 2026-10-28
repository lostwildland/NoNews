from __future__ import annotations

DDL = (
    """CREATE TABLE IF NOT EXISTS media_document_generations (
        item_id TEXT NOT NULL,
        generation INTEGER NOT NULL,
        document_hash TEXT NOT NULL,
        planned_output_hash TEXT,
        staging_path TEXT NOT NULL,
        staging_device INTEGER NOT NULL,
        staging_inode INTEGER NOT NULL,
        document_bytes INTEGER NOT NULL,
        source_url TEXT NOT NULL,
        metadata_json TEXT NOT NULL,
        provenance_json TEXT NOT NULL,
        expected_current_hash TEXT,
        state TEXT NOT NULL CHECK(state IN ('pending','committed')),
        raw_snapshot_id INTEGER,
        cleanup_state TEXT NOT NULL DEFAULT 'pending',
        cleanup_error TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(item_id, generation)
    )""",
    """CREATE UNIQUE INDEX IF NOT EXISTS media_document_one_pending
        ON media_document_generations(item_id) WHERE state='pending'""",
    """CREATE TABLE IF NOT EXISTS media_document_receipts (
        id INTEGER PRIMARY KEY,
        item_id TEXT NOT NULL,
        generation INTEGER NOT NULL DEFAULT 1,
        document_hash TEXT NOT NULL,
        planned_output_hash TEXT,
        status TEXT NOT NULL,
        raw_snapshot_id INTEGER,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
)

def ensure_schema(db):
    """Idempotent schema/import; never commit/rollback or change schema version."""
    for statement in DDL:
        db.execute(statement)
    # Preserve the initial R1 prototype table while importing its one generation.
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='media_documents'").fetchone():
        columns = ('item_id,document_hash,staging_path,staging_device,staging_inode,'
                   'document_bytes,source_url,metadata_json,provenance_json,'
                   'expected_current_hash,state,raw_snapshot_id,cleanup_state,cleanup_error,created_at')
        db.execute(f'INSERT OR IGNORE INTO media_document_generations (generation,{columns}) '
                   f'SELECT 1,{columns} FROM media_documents')
    columns = {row[1] for row in db.execute('PRAGMA table_info(media_document_receipts)')}
    if 'generation' not in columns:
        db.execute('ALTER TABLE media_document_receipts ADD COLUMN generation INTEGER NOT NULL DEFAULT 1')
    if 'planned_output_hash' not in columns:
        db.execute('ALTER TABLE media_document_receipts ADD COLUMN planned_output_hash TEXT')
