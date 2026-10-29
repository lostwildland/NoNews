from __future__ import annotations

from .core import retire_body_table

from .core import transaction

import re

APP_SCHEMA = """
-- Only the small bibliographic fields we verified ourselves live here. Feed
-- text (description, abstract, the RSS copy) is read back from FreshRSS when a
-- stage needs it, so nothing is archived twice.
CREATE TABLE IF NOT EXISTS item_metadata(
 item_id TEXT PRIMARY KEY REFERENCES items(id), metadata_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS stage_state(
 item_id TEXT REFERENCES items(id), stage TEXT, status TEXT NOT NULL,
 error TEXT, link TEXT, updated_at TEXT NOT NULL, PRIMARY KEY(item_id,stage));
-- A failure the reader has decided not to repair. Keyed by the row's own stamp
-- as well as its id, so acknowledging "this failure" never hides the next one:
-- a job that fails again writes a new updated_at and comes back.
CREATE TABLE IF NOT EXISTS failure_dismissals(
 kind TEXT NOT NULL, id TEXT NOT NULL, stamp TEXT NOT NULL, dismissed_at TEXT NOT NULL,
 PRIMARY KEY(kind,id));
CREATE TABLE IF NOT EXISTS editor_drafts(
 id TEXT PRIMARY KEY, item_id TEXT REFERENCES items(id), raw_snapshot_id INTEGER,
 prompt_version_id TEXT, provider TEXT, model TEXT, thinking_effort TEXT,
 input_hash TEXT, artifact_hash TEXT, created_at TEXT NOT NULL);
-- Drafts are read per item on every review read; without this each read scanned
-- the whole drafts table, which made the review queue quadratic. The reader
-- shows the newest draft, so the index also supplies that order.
CREATE INDEX IF NOT EXISTS editor_drafts_item ON editor_drafts(item_id, created_at);
CREATE TABLE IF NOT EXISTS private_raw_sources(
 snapshot_id INTEGER PRIMARY KEY REFERENCES raw_snapshots(id),
 item_id TEXT NOT NULL REFERENCES items(id),
 relative_path TEXT NOT NULL, sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS legacy_draft_imports(
 draft_id TEXT PRIMARY KEY REFERENCES editor_drafts(id) ON DELETE CASCADE,
 source_system TEXT NOT NULL, source_key TEXT NOT NULL, source_hash TEXT NOT NULL,
 imported_at TEXT NOT NULL, metadata_json TEXT NOT NULL,
 UNIQUE(source_system,source_key,source_hash));
CREATE TABLE IF NOT EXISTS prompt_versions(
 id TEXT PRIMARY KEY, kit_id TEXT NOT NULL, role TEXT NOT NULL,
 content TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS model_configs(
 kit_id TEXT, role TEXT, config_json TEXT NOT NULL, updated_at TEXT,
 PRIMARY KEY(kit_id,role));
CREATE TABLE IF NOT EXISTS integrations(
 key TEXT PRIMARY KEY, config_json TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS deliveries(
 item_id TEXT REFERENCES items(id), target TEXT, destination TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL, external_key TEXT, synced_hash TEXT, error TEXT, updated_at TEXT NOT NULL,
 draft_id TEXT,
 PRIMARY KEY(item_id,target,destination));
CREATE TABLE IF NOT EXISTS zotero_links(
 item_id TEXT PRIMARY KEY REFERENCES items(id), item_key TEXT NOT NULL UNIQUE,
 note_key TEXT NOT NULL UNIQUE, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
 available_at TEXT NOT NULL, synced_hash TEXT, error TEXT,
 adoption_source TEXT, adoption_status TEXT);
CREATE TABLE IF NOT EXISTS zotero_resolution(
 item_id TEXT PRIMARY KEY REFERENCES items(id), attempts INTEGER NOT NULL,
 status TEXT NOT NULL, available_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS news_notes(
 item_id TEXT PRIMARY KEY REFERENCES items(id), vault TEXT NOT NULL, path TEXT NOT NULL,
 updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS backlog_requests(
 id TEXT PRIMARY KEY, kit TEXT NOT NULL, window TEXT NOT NULL, status TEXT NOT NULL,
 planned INTEGER NOT NULL DEFAULT 0, queued INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 entry_ids_json TEXT, cursor INTEGER NOT NULL DEFAULT 0, error TEXT,
 rescore INTEGER NOT NULL DEFAULT 0, entry_routes_json TEXT);
CREATE TABLE IF NOT EXISTS activity(
 id INTEGER PRIMARY KEY, item_id TEXT, kind TEXT NOT NULL, message TEXT NOT NULL,
 status TEXT NOT NULL, created_at TEXT NOT NULL);
"""

def pending_artifact_migration(db) -> bool:
    """True while a database still carries the retired ``artifact_path`` column."""
    return "artifact_path" in {row[1] for row in db.execute("PRAGMA table_info(editor_drafts)")}

def drop_legacy_artifact_column(db) -> None:
    """Drop the retired ``artifact_path`` column. Idempotent.

    Draft bodies used to be files under the artifact store, then database rows,
    and now the literature draft file or the content store's ``draft_versions``
    holds them. The column named the old store, so it is retired with it; the
    bytes it named are left on disk rather than deleted by a startup pass,
    because removing an owned file is a separately reviewed cleanup, never part
    of opening a database.
    """
    if not pending_artifact_migration(db):
        return
    db.execute("ALTER TABLE editor_drafts DROP COLUMN artifact_path")

def _editor_drafts_allow_null_artifact_hash(db) -> bool:
    """True when an existing ``editor_drafts`` already accepts a NULL hash.

    A historical scaffold reconstructed by the migration has no old body baseline
    to record, so ``artifact_hash`` must stay NULL rather than be filled with a
    new body hash that would look like an original one. Older databases created
    the column ``NOT NULL``; SQLite cannot relax a constraint in place, so this
    one-time pass rebuilds only that table and keeps every row, column, index and
    foreign-key relation intact.
    """
    columns = {row[1]: row for row in db.execute("PRAGMA table_info(editor_drafts)")}
    artifact = columns.get("artifact_hash")
    if artifact is None:
        # An ancient shape without the column: nothing to relax and every read
        # already treats the baseline as unavailable.
        return True
    return not bool(artifact[3])

def _relax_editor_drafts_artifact_hash(db) -> bool:
    """Make ``editor_drafts.artifact_hash`` nullable once. Returns True when rebuilt."""
    if _editor_drafts_allow_null_artifact_hash(db):
        return False
    row = db.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='editor_drafts'").fetchone()
    if row is None or not row[0]:
        return False
    ddl = str(row[0])
    relaxed = re.sub(r"(\bartifact_hash\b\s+TEXT)\s+NOT NULL", r"\1", ddl,
                     count=1, flags=re.IGNORECASE)
    if relaxed == ddl:
        raise RuntimeError("editor_drafts.artifact_hash constraint could not be relaxed safely")
    relaxed = re.sub(
        r"^CREATE TABLE\s+(?:IF NOT EXISTS\s+)?[\"'`\[]?editor_drafts[\"'`\]]?",
        "CREATE TABLE editor_drafts_nullable", relaxed, count=1, flags=re.IGNORECASE)
    columns = [row[1] for row in db.execute("PRAGMA table_info(editor_drafts)")]
    quoted = ",".join('"' + name.replace('"', '""') + '"' for name in columns)
    preserved_sql = [str(row[0]) for row in db.execute(
        "SELECT sql FROM sqlite_master WHERE type IN ('index','trigger') "
        "AND tbl_name='editor_drafts' AND sql IS NOT NULL ORDER BY type, name")]
    previous_foreign_keys = int(db.execute("PRAGMA foreign_keys").fetchone()[0])
    if db.in_transaction:
        raise RuntimeError("editor_drafts rebuild must run outside a transaction")
    db.execute("PRAGMA foreign_keys=OFF")
    try:
        with transaction(db):
            db.execute(relaxed)
            db.execute(f"INSERT INTO editor_drafts_nullable({quoted}) "
                       f"SELECT {quoted} FROM editor_drafts")
            db.execute("DROP TABLE editor_drafts")
            db.execute("ALTER TABLE editor_drafts_nullable RENAME TO editor_drafts")
            # Recreate every index and trigger that belonged to the old table.
            for statement in preserved_sql:
                db.execute(statement)
            db.execute("CREATE INDEX IF NOT EXISTS editor_drafts_item "
                       "ON editor_drafts(item_id, created_at)")
            if "manual_revision_id" in columns:
                db.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS editor_drafts_manual_revision "
                    "ON editor_drafts(manual_revision_id) WHERE manual_revision_id IS NOT NULL")
            violations = [
                row for row in db.execute("PRAGMA foreign_key_check").fetchall()
                if str(row[2]) == "editor_drafts"]
            if violations:
                raise RuntimeError("editor_drafts rebuild would break a foreign key")
    finally:
        db.execute("PRAGMA foreign_keys=" + ("ON" if previous_foreign_keys else "OFF"))
    if not _editor_drafts_allow_null_artifact_hash(db):
        raise RuntimeError("editor_drafts.artifact_hash is still NOT NULL after the rebuild")
    return True

def ensure_schema(db, *, artifacts: ArtifactStore | None = None) -> None:
    """Create the application tables and run their migrations. Idempotent."""
    db.executescript(APP_SCHEMA)
    if "model_source_json" not in {row[1] for row in db.execute("PRAGMA table_info(editor_drafts)")}:
        db.execute("ALTER TABLE editor_drafts ADD COLUMN model_source_json TEXT")
    # Human Final belonged to the retired reader's own editor. Nothing writes
    # it, it is not a version the user can see, and its draft is not kept.
    db.execute("DROP TABLE IF EXISTS human_final")
    # Kit rename: existing databases still carry the old media_type column.
    for table in ("prompt_versions", "model_configs"):
        columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
        if "kit_id" not in columns and "media_type" in columns:
            db.execute(f"ALTER TABLE {table} RENAME COLUMN media_type TO kit_id")
    columns = {row[1] for row in db.execute("PRAGMA table_info(zotero_links)")}
    if "adoption_source" not in columns:
        db.execute("ALTER TABLE zotero_links ADD COLUMN adoption_source TEXT")
    if "adoption_status" not in columns:
        db.execute("ALTER TABLE zotero_links ADD COLUMN adoption_status TEXT")
    # A failed stage can name the page a person has to open to finish it, which
    # only the source-browser failures do. Older databases have no column for it.
    if "link" not in {row[1] for row in db.execute("PRAGMA table_info(stage_state)")}:
        db.execute("ALTER TABLE stage_state ADD COLUMN link TEXT")
    # Feed text used to be archived beside the item; those columns and the
    # per-observation copy are gone, and only the small metadata survives.
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='item_inputs'").fetchone():
        db.execute("""INSERT OR IGNORE INTO item_metadata(item_id,metadata_json)
            SELECT item_id,metadata_json FROM item_inputs""")
        db.execute("DROP TABLE item_inputs")
    db.execute("DROP TABLE IF EXISTS observation_inputs")
    # Feed subscription changes are made in native FreshRSS; this queue and its
    # command table are gone with that HTTP surface.
    db.execute("DROP TABLE IF EXISTS feed_commands")
    # The draft body's home is the content store's ``draft_versions`` row, or the
    # literature draft file for an item the store does not hold. The retired
    # ``draft_texts`` table is dropped once its rows have been moved out.
    retire_body_table(db, "draft_texts")
    # Draft bodies used to be files under the artifact store; the column that
    # named them is retired with that store. A caller without an artifact store
    # still gets the column dropped: it names a body nothing reads any more.
    drop_legacy_artifact_column(db)
    if "manual_source_id" not in {row[1] for row in db.execute("PRAGMA table_info(editor_drafts)")}:
        db.execute("ALTER TABLE editor_drafts ADD COLUMN manual_source_id TEXT")
    if "manual_revision_id" not in {row[1] for row in db.execute("PRAGMA table_info(editor_drafts)")}:
        db.execute("ALTER TABLE editor_drafts ADD COLUMN manual_revision_id TEXT")
    # A migrated draft scaffold has no historical body baseline, so the column
    # must accept NULL; newly created databases are already nullable.
    _relax_editor_drafts_artifact_hash(db)
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS editor_drafts_manual_revision ON editor_drafts(manual_revision_id) WHERE manual_revision_id IS NOT NULL")
    deliveries = {row[1] for row in db.execute("PRAGMA table_info(deliveries)")}
    if "draft_id" not in deliveries:
        db.execute("ALTER TABLE deliveries ADD COLUMN draft_id TEXT")
    if "position" not in deliveries:
        db.execute("ALTER TABLE deliveries ADD COLUMN position INTEGER")
    backlog_columns = {row[1] for row in db.execute("PRAGMA table_info(backlog_requests)")}
    if "entry_ids_json" not in backlog_columns:
        db.execute("ALTER TABLE backlog_requests ADD COLUMN entry_ids_json TEXT")
    if "cursor" not in backlog_columns:
        db.execute("ALTER TABLE backlog_requests ADD COLUMN cursor INTEGER NOT NULL DEFAULT 0")
    if "error" not in backlog_columns:
        db.execute("ALTER TABLE backlog_requests ADD COLUMN error TEXT")
    if "rescore" not in backlog_columns:
        db.execute("ALTER TABLE backlog_requests ADD COLUMN rescore INTEGER NOT NULL DEFAULT 0")
    if "entry_routes_json" not in backlog_columns:
        db.execute("ALTER TABLE backlog_requests ADD COLUMN entry_routes_json TEXT")
    # Mapping between a stable paper item, its fixed citekey and the Obsidian
    # literature files. Metadata only: switching an item never writes a vault
    # file, and this pass runs on every database upgrade without migrating or
    # deleting any body.
    from .literature_mapping import ensure_schema as ensure_literature_mapping
    ensure_literature_mapping(db)
