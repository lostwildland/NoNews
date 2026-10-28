"""One versioned schema pass per database, instead of DDL on every request.

Every owner used to create its tables in ``__init__``. Those constructors run on
every HTTP request and on every worker iteration, and SQLite takes the write lock
for ``CREATE TABLE IF NOT EXISTS`` even when the table already exists: measured
against a writer holding ``BEGIN IMMEDIATE``, a construction blocked for the whole
30s busy timeout and then failed with "database is locked". The work now happens
once, recorded in ``schema_meta.schema_version``; afterwards opening the database
costs one indexed read.

Each owner exposes ``ensure_schema(db)``, which is idempotent by construction: it
only creates or alters what is missing. The pass is therefore safe to re-run after
a crash that happened before the version was stamped.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing

# Bump when any ensure_schema below changes shape. A database already at this
# version skips the whole pass.
# 36: ai_feed_settings.subscription_state -- a feed FreshRSS still holds but the
# GReader subscription list no longer returns stays on the source list.
# 37: ai_feed_settings.contract_origin -- history seeding may fill a feed's
# media type/Kit from IO's identity, but must never re-derive one a person
# saved (an explicit clear has to stay cleared).
# 38: Magpie per-draft provenance and pending-job mapping blocks.
# 39: immutable Editor-only Magpie target pin on a processing job.
# 40: Reject image cleanup progress and object deletion generations.
# 41: daily deletion keeps no image backup paths.
# 42: native source observations, processing contexts and feed policies.
# 43: complete native policy context snapshots and identity evidence validation.
# 44: retain raw identity evidence and enforce media-qualified identity rules.
# 45: durable native context result associations and unresolved raw evidence.
# 46: native context results and raw observation identity columns.
SCHEMA_VERSION = 46
_VERSION_KEY = "schema_version"


def version(db: sqlite3.Connection) -> int:
    """The recorded schema version, or 0 for a database that predates it."""
    try:
        row = db.execute("SELECT value FROM schema_meta WHERE key=?", (_VERSION_KEY,)).fetchone()
    except sqlite3.OperationalError:
        return 0
    if row is None:
        return 0
    try:
        return int(row[0])
    except (TypeError, ValueError):
        return 0


def stamp(db: sqlite3.Connection, value: int = SCHEMA_VERSION) -> None:
    db.execute("""INSERT INTO schema_meta(key,value) VALUES (?,?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value""", (_VERSION_KEY, str(value)))


class UnsupportedSchemaError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require_supported_database(db: sqlite3.Connection) -> None:
    current = version(db)
    if current > SCHEMA_VERSION:
        raise UnsupportedSchemaError('schema_newer')
    if current not in {SCHEMA_VERSION - 5, SCHEMA_VERSION - 4, SCHEMA_VERSION - 3, SCHEMA_VERSION - 2, SCHEMA_VERSION - 1, SCHEMA_VERSION} and db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' LIMIT 1").fetchone():
        raise UnsupportedSchemaError('schema_migration_required')



def validate_structure(db: sqlite3.Connection) -> None:
    """Require the current IO write invariants without repairing imported data."""
    from .schema_semantics import table_semantics
    try:
        with closing(sqlite3.connect(':memory:')) as reference:
            ensure(reference)
            names = [row[0] for row in reference.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            canonical = {name.casefold() for name in names}
            if any(table.casefold() in canonical for table, in db.execute(
                    "SELECT tbl_name FROM sqlite_master WHERE type='trigger'")):
                raise UnsupportedSchemaError('schema_migration_required')
            existing = {row[0].casefold(): row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            for name in names:
                actual_name = existing.get(name.casefold())
                if actual_name is None:
                    raise ValueError('required table missing')
                expected = table_semantics(reference, name)
                current = table_semantics(db, actual_name)
                for kind in ('primary_key', 'rowid_alias'):
                    if current[kind] != expected[kind]:
                        raise ValueError('required key missing')
                for kind in ('affinities', 'defaults', 'hidden'):
                    if any(column not in current['affinities'] or current[kind].get(column) != expected[kind].get(column)
                           for column in expected['affinities']):
                        raise ValueError('required column contract missing')
                for kind in ('not_null', 'unique', 'foreign_keys', 'checks'):
                    if not all(value in current[kind] for value in expected[kind]):
                        raise ValueError('required constraint missing')
                for column in set(current['not_null']) - set(expected['not_null']):
                    if column in expected['affinities'] or current['defaults'].get(column) in (None, ['null']):
                        raise ValueError('unsupported additional not-null constraint')
                for kind in ('foreign_keys', 'checks'):
                    if any(value not in expected[kind] for value in current[kind]):
                        raise ValueError('unsupported additional constraint')
                for keys, predicate in current['unique']:
                    if [keys, predicate] in expected['unique']:
                        continue
                    if predicate is not None or any(column in expected['affinities'] or column in current['not_null'] or current['defaults'].get(column) not in (None, ['null']) for column, _ in keys):
                        raise ValueError('unsupported additional uniqueness constraint')
    except UnsupportedSchemaError:
        raise
    except ValueError as exc:
        raise UnsupportedSchemaError('schema_incomplete') from exc


class _TransactionalScripts:
    def __init__(self, db):
        self.db = db

    def __getattr__(self, name):
        return getattr(self.db, name)

    def executescript(self, script):
        statement = ''
        for line in script.splitlines(keepends=True):
            statement += line
            if sqlite3.complete_statement(statement):
                self.db.execute(statement)
                statement = ''
        if statement.strip():
            raise ValueError('Incomplete schema statement')


def ensure(db: sqlite3.Connection, *, artifacts=None) -> bool:
    """Initialize empty data atomically, retaining unknown historical schemas."""
    db.execute('BEGIN IMMEDIATE')
    try:
        changed = _ensure(_TransactionalScripts(db), artifacts=artifacts)
        db.execute('COMMIT')
        return changed
    except BaseException:
        db.execute('ROLLBACK')
        raise


def _ensure(db, *, artifacts=None) -> bool:
    require_supported_database(db)
    from . import (content_store, core, delivery, feed_settings, folders, jobs,
                   legacy_content_migration, literature, media_jobs, media_raw_activation,
                   media_store, native_source, news_media, pipeline, projection, reading_notes,
                   reconciliation, reject_cleanup, service, settings, zotero)
    if version(db) == SCHEMA_VERSION:
        return False

    core.ensure_schema(db)
    settings.ensure_schema(db)
    service.ensure_schema(db, artifacts=artifacts)
    # Bodies and draft versions live in the database; the store's tables reference
    # ``raw_snapshots`` and ``editor_drafts``, so they are created after both.
    content_store.ensure_schema(db)
    # The migration ledger records what was imported from the old vault files. It
    # stores evidence, never body text, so it is created with the rest of the
    # schema and costs one lookup when it already exists.
    legacy_content_migration.ensure_schema(db)
    jobs.ensure_schema(db)
    delivery.ensure_schema(db)
    projection.ensure_schema(db)
    pipeline.ensure_schema(db)
    zotero.ensure_schema(db)
    reconciliation.ensure_schema(db)
    folders.ensure_schema(db)
    # Feed-level processing settings are the routing authority; the folder table
    # above survives as navigation and bulk-edit metadata only.
    feed_settings.ensure_schema(db)
    literature.ensure_schema(db)
    media_store.ensure_schema(db)
    media_jobs.ensure_schema(db)
    media_raw_activation.ensure_schema(db)
    native_source.ensure_schema(db)
    news_media.ensure_schema(db)
    reading_notes.ensure_schema(db)
    # Reject cleanup progress/audit and explicit maintenance backup records.
    # Requests live in core because the human decision creates them atomically.
    reject_cleanup.ensure_schema(db)
    stamp(db)
    return True
