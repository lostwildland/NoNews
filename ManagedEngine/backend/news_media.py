from __future__ import annotations

def ensure_schema(db):
    """DDL only; the parent migration owns schema version and transaction."""
    db.execute('''CREATE TABLE IF NOT EXISTS media_derivatives (
        original_key TEXT NOT NULL REFERENCES media_objects(key),
        derived_key TEXT NOT NULL REFERENCES media_objects(key),
        purpose TEXT NOT NULL, detail_json TEXT NOT NULL,
        PRIMARY KEY(original_key,derived_key,purpose))''')
