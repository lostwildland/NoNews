from __future__ import annotations

from pathlib import Path

import sqlite3

from typing import Callable

from typing import Iterator

import uuid

from contextlib import contextmanager

from datetime import UTC

from datetime import datetime

from datetime import timedelta

def utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS feeds (
  id TEXT PRIMARY KEY, freshrss_feed_id TEXT NOT NULL UNIQUE, feed_url TEXT,
  title TEXT NOT NULL, current_media_type TEXT, first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL, subscription_status TEXT NOT NULL DEFAULT 'active',
  unsubscribed_at TEXT
);
-- The feed list is ordered by title in the settings and integration views.
CREATE INDEX IF NOT EXISTS feeds_title ON feeds(title);
CREATE TABLE IF NOT EXISTS items (
  id TEXT PRIMARY KEY, media_type TEXT NOT NULL CHECK(media_type IN ('news','paper','newsletter','podcast','video')),
  canonical_url TEXT, title TEXT, published_at TEXT, first_ingested_at TEXT NOT NULL,
  review_date TEXT NOT NULL, current_raw_snapshot_id INTEGER,
  human_review_status TEXT NOT NULL DEFAULT 'pending', human_decision TEXT,
  human_curator_run_id TEXT, reviewed_at TEXT, starred INTEGER NOT NULL DEFAULT 0,
  ever_starred INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  review_generation INTEGER NOT NULL DEFAULT 0
);
-- Zotero delivery walks every starred item on each pass.
CREATE INDEX IF NOT EXISTS items_starred ON items(starred);
CREATE TABLE IF NOT EXISTS item_identities (
  id INTEGER PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id), media_type TEXT NOT NULL,
  identity_type TEXT NOT NULL, identity_value TEXT NOT NULL, created_at TEXT NOT NULL,
  UNIQUE(media_type, identity_type, identity_value)
);
CREATE INDEX IF NOT EXISTS item_identities_item ON item_identities(item_id);
CREATE TABLE IF NOT EXISTS entry_observations (
  id INTEGER PRIMARY KEY, freshrss_entry_id TEXT NOT NULL UNIQUE, feed_id TEXT NOT NULL REFERENCES feeds(id),
  item_id TEXT NOT NULL REFERENCES items(id), original_url TEXT, ingested_at TEXT NOT NULL, published_at TEXT
);
-- Every per-item read joins on item_id. Without this index each item read
-- scanned the whole table, which made the reader quadratic in the archive size.
CREATE INDEX IF NOT EXISTS entry_observations_item ON entry_observations(item_id);
-- The reader lists newest-first; this index also supplies the order.
CREATE INDEX IF NOT EXISTS entry_observations_recent ON entry_observations(ingested_at DESC, id DESC);
CREATE TABLE IF NOT EXISTS feed_items (
  feed_id TEXT NOT NULL REFERENCES feeds(id), item_id TEXT NOT NULL REFERENCES items(id),
  first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, PRIMARY KEY(feed_id, item_id)
);
CREATE TABLE IF NOT EXISTS raw_snapshots (
  id INTEGER PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id), path TEXT NOT NULL,
  source_hash TEXT NOT NULL, retrieved_at TEXT NOT NULL, created_at TEXT NOT NULL,
  provenance TEXT NOT NULL DEFAULT '',
  UNIQUE(item_id, source_hash)
);
CREATE TABLE IF NOT EXISTS curator_runs (
  id TEXT PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id), raw_snapshot_id INTEGER,
  prompt_version_id TEXT, provider TEXT, model TEXT, thinking_effort TEXT, input_hash TEXT,
  score REAL, ai_decision TEXT, reason TEXT, result_json TEXT, status TEXT NOT NULL,
  started_at TEXT NOT NULL, finished_at TEXT, error TEXT
);
CREATE INDEX IF NOT EXISTS curator_runs_latest ON curator_runs(item_id, finished_at DESC, id DESC);
CREATE TABLE IF NOT EXISTS human_reviews (
  id INTEGER PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id), curator_run_id TEXT,
  event_type TEXT NOT NULL, decision TEXT, action_source TEXT NOT NULL, created_at TEXT NOT NULL,
  idempotency_key TEXT UNIQUE
);
-- A selection fact recorded by the new scoring flow when a valid run reaches the
-- Kit threshold.  It is deliberately separate from ``curator_runs``: a query over
-- historical scores would auto-activate the old backlog, while this row exists
-- only for a run the new flow actually performed.  A later low score never
-- removes it, and a human Reject still outranks it.
CREATE TABLE IF NOT EXISTS literature_selections (
  item_id TEXT PRIMARY KEY REFERENCES items(id), curator_run_id TEXT NOT NULL,
  score REAL NOT NULL, threshold REAL NOT NULL, selected_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS star_events (
  id INTEGER PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id), starred INTEGER NOT NULL,
  action_source TEXT NOT NULL, created_at TEXT NOT NULL, idempotency_key TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS unstar_cleanup (
  id TEXT PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id),
  status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
  available_at TEXT NOT NULL, error TEXT
);
-- A human-confirmed final non-selection of a Paper records one durable cleanup
-- REQUEST here, in the same committed transaction as the decision. It is never
-- the cleanup itself: it starts (and stays) in ``hold`` until a separately
-- reviewed per-asset manifest, a coherent backup, an independent restore anchor
-- and the adoption/annotation/protection facts are all satisfied. ``doing the
-- cleanup`` is deliberately not representable by this row's statuses; an
-- executor is a separate, gated owner that does not exist yet.
CREATE TABLE IF NOT EXISTS literature_cleanup_requests (
  id TEXT PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id),
  status TEXT NOT NULL DEFAULT 'hold'
    CHECK(status IN ('hold','pending_review','executing','cancelled','executed')),
  cause TEXT NOT NULL, action_source TEXT, command_id TEXT, review_id INTEGER,
  ai_run_id TEXT, ai_decision TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  due_at TEXT NOT NULL DEFAULT '', started_at TEXT, completed_at TEXT,
  attempts INTEGER NOT NULL DEFAULT 0, error TEXT, retry_after TEXT,
  backup_id TEXT, execution_token TEXT, tombstone_json TEXT NOT NULL DEFAULT '',
  review_generation INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS literature_cleanup_requests_review
  ON literature_cleanup_requests(review_id);
CREATE INDEX IF NOT EXISTS literature_cleanup_requests_item
  ON literature_cleanup_requests(item_id, status);
CREATE TABLE IF NOT EXISTS commands (
  id TEXT PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id), command_type TEXT NOT NULL,
  payload TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL DEFAULT 'pending',
  idempotency_key TEXT NOT NULL UNIQUE, requested_at TEXT NOT NULL, undo_deadline TEXT NOT NULL,
  executed_at TEXT, error TEXT
);
CREATE INDEX IF NOT EXISTS commands_pending ON commands(status, undo_deadline);
CREATE INDEX IF NOT EXISTS commands_item ON commands(item_id);
CREATE TABLE IF NOT EXISTS command_batches (
  id TEXT PRIMARY KEY, result_json TEXT NOT NULL
);
"""

def retire_body_table(db: sqlite3.Connection, name: str) -> None:
    """Drop a retired body table once it holds no rows. Idempotent.

    ``raw_texts``/``draft_texts`` used to be the only copy of a Raw or a draft
    body. Neither is a body store any more -- a body lives in
    ``backend.content_store`` (``body_versions``) or in the item's literature
    file -- so nothing reads or writes either table. The drop is deliberately
    conditional on emptiness: an archived database (a backup, or the copy a
    reconciliation tool inspects) still carries the historical bodies it was
    taken with, and opening it must not destroy them. A live database reaches
    the empty state because the migration that moved its bodies out already ran.
    """
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                  (name,)).fetchone() is None:
        return
    if db.execute(f"SELECT 1 FROM {name} LIMIT 1").fetchone() is None:
        db.execute(f"DROP TABLE {name}")

def _rebuild_cleanup_requests(db: sqlite3.Connection) -> None:
    """Rebuild the request table once to admit the ``executed`` status.

    The old table's CHECK constraint is part of its stored definition, so no
    ALTER can widen it. Rows are copied by their original columns; the new
    columns are added by :func:`ensure_schema` immediately afterwards. The
    indexes are dropped before the rename because SQLite keeps their names with
    the renamed table.
    """
    db.executescript("""
        DROP INDEX IF EXISTS literature_cleanup_requests_review;
        DROP INDEX IF EXISTS literature_cleanup_requests_item;
        DROP INDEX IF EXISTS literature_cleanup_requests_due;
        ALTER TABLE literature_cleanup_requests RENAME TO literature_cleanup_requests_old;
        CREATE TABLE literature_cleanup_requests (
          id TEXT PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id),
          status TEXT NOT NULL DEFAULT 'hold'
            CHECK(status IN ('hold','pending_review','executing','cancelled','executed')),
          cause TEXT NOT NULL, action_source TEXT, command_id TEXT, review_id INTEGER,
          ai_run_id TEXT, ai_decision TEXT,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
          due_at TEXT NOT NULL DEFAULT '', started_at TEXT, completed_at TEXT,
          attempts INTEGER NOT NULL DEFAULT 0, error TEXT, retry_after TEXT,
          backup_id TEXT, execution_token TEXT, tombstone_json TEXT NOT NULL DEFAULT '',
          review_generation INTEGER NOT NULL DEFAULT 0
        );
        INSERT INTO literature_cleanup_requests
          (id,item_id,status,cause,action_source,command_id,review_id,ai_run_id,ai_decision,
           created_at,updated_at)
          SELECT id,item_id,status,cause,action_source,command_id,review_id,ai_run_id,ai_decision,
                 created_at,updated_at
          FROM literature_cleanup_requests_old;
        DROP TABLE literature_cleanup_requests_old;
        CREATE UNIQUE INDEX literature_cleanup_requests_review
          ON literature_cleanup_requests(review_id);
        CREATE INDEX literature_cleanup_requests_item
          ON literature_cleanup_requests(item_id, status);
    """)

def ensure_schema(db: sqlite3.Connection) -> None:
    """Create the core tables. Idempotent; run by the schema pass, not per request."""
    db.executescript(SCHEMA)
    # The Raw body's database copy is not this table any more: a body lives in
    # ``content_store``'s ``body_versions`` or in the item's literature file. The
    # table is retired once its rows have been moved out.
    retire_body_table(db, "raw_texts")
    # The folder name a Raw takes in the vault. Eight characters, because a
    # 32-character uuid is unreadable there and truncating one collides within
    # a few tens of thousands of items; assigned once and never reused.
    columns = {row[1] for row in db.execute("PRAGMA table_info(items)")}
    if "public_id" not in columns:
        db.execute("ALTER TABLE items ADD COLUMN public_id TEXT")
    if "review_generation" not in columns:
        # Every committed human decision increments this. A queued job records
        # the generation it started under, so a Reject (or a later Select) makes
        # a late result stale instead of letting it write the content back.
        db.execute("ALTER TABLE items ADD COLUMN review_generation INTEGER NOT NULL DEFAULT 0")
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS items_public_id ON items(public_id)")
    # A database written before this package has the old status CHECK, which does
    # not admit ``executed``. ALTER TABLE cannot widen a CHECK, so the request
    # table is rebuilt once with the same rows and the new definition.
    request_sql = db.execute("""SELECT sql FROM sqlite_master
        WHERE type='table' AND name='literature_cleanup_requests'""").fetchone()
    if request_sql is not None and "'executed'" not in (request_sql[0] or ""):
        _rebuild_cleanup_requests(db)
    cleanup_columns = {row[1] for row in db.execute("PRAGMA table_info(literature_cleanup_requests)")}
    for name, definition in (
            ("due_at", "TEXT NOT NULL DEFAULT ''"),
            ("started_at", "TEXT"), ("completed_at", "TEXT"),
            ("attempts", "INTEGER NOT NULL DEFAULT 0"), ("error", "TEXT"),
            ("retry_after", "TEXT"), ("backup_id", "TEXT"), ("execution_token", "TEXT"),
            ("tombstone_json", "TEXT NOT NULL DEFAULT ''"),
            ("review_generation", "INTEGER NOT NULL DEFAULT 0")):
        if name not in cleanup_columns:
            db.execute(f"ALTER TABLE literature_cleanup_requests ADD COLUMN {name} {definition}")
    # A request recorded by the pre-executor package has no due time. Its seven
    # day window starts at the decision it already records, never at upgrade time.
    for row in db.execute("""SELECT id,created_at FROM literature_cleanup_requests
        WHERE due_at=''""").fetchall():
        try:
            due = (datetime.fromisoformat(row[1])
                   + timedelta(days=InformationDB.CLEANUP_RECOVERY_DAYS))
        except (TypeError, ValueError):
            continue
        db.execute("UPDATE literature_cleanup_requests SET due_at=? WHERE id=?",
                   (due.isoformat(timespec="seconds"), row[0]))
    # The due scan runs in the existing command worker; without this index it
    # would scan every historical request on each pass.
    db.execute("""CREATE INDEX IF NOT EXISTS literature_cleanup_requests_due
        ON literature_cleanup_requests(status, due_at)""")
    columns = {row[1] for row in db.execute("PRAGMA table_info(raw_snapshots)")}
    if "vault_exported_at" not in columns:
        db.execute("ALTER TABLE raw_snapshots ADD COLUMN vault_exported_at TEXT")
    if "provenance" not in columns:
        # A historical index reconciliation may create a snapshot whose source
        # is not a publisher fetch. Keep that fact on the provenance row instead
        # of letting a synthetic source_hash look like an acquired document.
        db.execute("ALTER TABLE raw_snapshots ADD COLUMN provenance TEXT NOT NULL DEFAULT ''")
    # The review queue and the backlog both filter on review status and read in
    # arrival order; without this each page load scans every item.
    db.execute("CREATE INDEX IF NOT EXISTS items_review ON items(human_review_status, first_ingested_at, id)")
    # The half-second worker loops (schedule_selected, backlog counts) ask for
    # decided items only; this keeps that lookup off a full table scan.
    db.execute("CREATE INDEX IF NOT EXISTS items_decision ON items(human_review_status, human_decision)")

def transaction(db: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """One write transaction: commit on a clean exit, roll back on any other.

    ``BaseException`` rather than ``Exception``: an interrupt or a process exit
    between BEGIN and COMMIT must not leave the connection inside an open
    transaction, which turns the next BEGIN into "cannot start a transaction
    within a transaction".
    """
    savepoint = "nested_" + uuid.uuid4().hex if db.in_transaction else None
    db.execute("SAVEPOINT " + savepoint if savepoint else "BEGIN IMMEDIATE")
    try:
        yield db
    except BaseException:
        try:
            db.execute("ROLLBACK TO " + savepoint if savepoint else "ROLLBACK")
            if savepoint:
                db.execute("RELEASE " + savepoint)
        except sqlite3.Error:
            pass
        raise
    else:
        db.execute("RELEASE " + savepoint if savepoint else "COMMIT")

class InformationDB:

    def __init__(self, path: str | Path=':memory:', *, clock: Callable[[], str]=utcnow, read_only: bool=False) -> None:
        self.path = str(path)
        self.clock = clock
        self._selection_schema_ready = False
        if read_only:
            self.db = sqlite3.connect(f'file:{Path(path).resolve()}?mode=ro', uri=True, timeout=30, isolation_level=None)
        else:
            self.db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA busy_timeout=30000')
        if not read_only:
            self.db.execute('PRAGMA journal_mode=WAL')
            self.db.execute('PRAGMA synchronous=NORMAL')
            self.db.execute('PRAGMA cache_size=-65536')
            self.db.execute('PRAGMA mmap_size=268435456')
            self.db.execute('PRAGMA temp_store=MEMORY')
            self.db.execute('PRAGMA journal_size_limit=67108864')
        if not read_only:
            from . import schema as schema_pass
            schema_pass.ensure(self.db)

    def transaction(self):
        """See :func:`transaction`. Reads better at the call site."""
        return transaction(self.db)

    def close(self) -> None:
        try:
            self.db.execute('PRAGMA optimize')
        except sqlite3.Error:
            pass
        self.db.close()

    def __enter__(self) -> 'InformationDB':
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _now(self) -> str:
        return self.clock()
    CLEANUP_RECOVERY_DAYS = 7
