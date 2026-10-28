from __future__ import annotations

DDL = ('''CREATE TABLE IF NOT EXISTS media_raw_activation_intents (
    id TEXT PRIMARY KEY, item_id TEXT NOT NULL, expected_snapshot_id INTEGER,
    old_mapping_json TEXT NOT NULL, old_authority_json TEXT NOT NULL, citekey TEXT NOT NULL,
    candidate_hash TEXT NOT NULL, preimage_json TEXT, quarantine_path TEXT,
    state TEXT NOT NULL, snapshot_id INTEGER, receipt_id TEXT)''',)

def ensure_schema(db):
    for sql in DDL:
        db.execute(sql)
    columns = {row[1] for row in db.execute('PRAGMA table_info(media_raw_activation_intents)')}
    if 'quarantine_path' not in columns:
        db.execute('ALTER TABLE media_raw_activation_intents ADD COLUMN quarantine_path TEXT')
