from __future__ import annotations

SCHEMA = """
-- One row per paper switched to the Obsidian file layer. A row means the Raw and
-- the AI drafts live in the vault; no row means the item still reads the legacy
-- database bodies. Metadata only: switching never writes or migrates a file.
CREATE TABLE IF NOT EXISTS literature_files(
 item_id TEXT PRIMARY KEY REFERENCES items(id),
 citekey TEXT NOT NULL UNIQUE,
 status TEXT NOT NULL,
 source TEXT NOT NULL,
 evidence_json TEXT NOT NULL DEFAULT '{}',
 conditional_writer TEXT NOT NULL,
 enabled_at TEXT NOT NULL,
 updated_at TEXT NOT NULL);
-- Which archived Raw snapshot the single ``raw/<citekey>/<citekey>_raw.md`` holds.
-- A snapshot archived before the switch has no row and is not silently mapped.
CREATE TABLE IF NOT EXISTS literature_raws(
 snapshot_id INTEGER PRIMARY KEY REFERENCES raw_snapshots(id),
 item_id TEXT NOT NULL REFERENCES items(id),
 citekey TEXT NOT NULL,
 path TEXT NOT NULL,
 file_sha256 TEXT NOT NULL,
 bound_at TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS literature_raws_item ON literature_raws(item_id);
-- The Service draft id (stable public identity) and the independent AI draft
-- file it maps to. Both ids are kept in full: the file's own draft_id is derived
-- by the file layer and is not guaranteed to equal the Service id.
CREATE TABLE IF NOT EXISTS literature_drafts(
 draft_id TEXT PRIMARY KEY REFERENCES editor_drafts(id),
 item_id TEXT NOT NULL REFERENCES items(id),
 citekey TEXT NOT NULL,
 file_identity TEXT NOT NULL,
 file_draft_id TEXT NOT NULL,
 path TEXT NOT NULL,
 version INTEGER NOT NULL,
 payload_sha256 TEXT NOT NULL,
 file_sha256 TEXT NOT NULL,
 bound_at TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS literature_drafts_identity
 ON literature_drafts(item_id, file_identity);
CREATE UNIQUE INDEX IF NOT EXISTS literature_drafts_file
 ON literature_drafts(citekey, file_draft_id);
CREATE INDEX IF NOT EXISTS literature_drafts_item ON literature_drafts(item_id);
"""

_RESERVATION_TABLE = """
-- One row per IO paper whose immutable Obsidian file key was read from BBT.
-- Metadata only: reserving never writes, moves or claims a vault file, and a
-- database without this row is a legacy file-authority row, not an error.
CREATE TABLE IF NOT EXISTS literature_file_keys(
 item_id TEXT PRIMARY KEY REFERENCES items(id),
 file_key TEXT NOT NULL UNIQUE,
 status TEXT NOT NULL,
 source TEXT NOT NULL,
 origin_parent_library_id TEXT NOT NULL,
 origin_parent_item_key TEXT NOT NULL,
 origin_parent_identity TEXT NOT NULL,
 origin_evidence_json TEXT NOT NULL DEFAULT '{}',
 active_parent_library_id TEXT NOT NULL,
 active_parent_item_key TEXT NOT NULL,
 active_parent_identity TEXT NOT NULL,
 active_source TEXT NOT NULL,
 active_evidence_json TEXT NOT NULL DEFAULT '{}',
 initial_citation_key TEXT NOT NULL,
 current_citation_key TEXT NOT NULL,
 drift_state TEXT NOT NULL,
 drift_reason TEXT,
 reserved_at TEXT NOT NULL,
 citation_key_updated_at TEXT NOT NULL,
 parent_updated_at TEXT NOT NULL,
 updated_at TEXT NOT NULL)"""

_RESERVATION_INDEX = """CREATE UNIQUE INDEX IF NOT EXISTS literature_file_keys_current
 ON literature_file_keys(current_citation_key)"""

_RESERVATION_STATEMENTS = (_RESERVATION_TABLE, _RESERVATION_INDEX)

RESERVATION_SCHEMA = ";\n".join(_RESERVATION_STATEMENTS) + ";\n"

def ensure_schema(db) -> None:
    """Create the mapping tables. Idempotent; never touches a file."""
    db.executescript(SCHEMA + RESERVATION_SCHEMA)
