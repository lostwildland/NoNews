from __future__ import annotations

SCHEMA = """
CREATE TABLE IF NOT EXISTS ai_folder_profiles (
  folder TEXT PRIMARY KEY,
  profile TEXT,
  enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)),
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ai_kits (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  content_type TEXT NOT NULL,
  threshold REAL NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
"""

def ensure_schema(db) -> None:
    """Create the folder/kit tables. Idempotent; run by the schema pass."""
    db.executescript(SCHEMA)
    columns = {row[1] for row in db.execute("PRAGMA table_info(ai_kits)")}
    if "content_types_json" not in columns:
        # One Kit may serve several media types (prompts and models stay Kit-wide).
        # Added in place so every existing Kit keeps its single content type.
        db.execute("ALTER TABLE ai_kits ADD COLUMN content_types_json TEXT")
