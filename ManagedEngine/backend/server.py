"""Managed settings-scope slice of the IO Application public dispatch."""
from pathlib import Path
from contextlib import closing
import sqlite3
import base64
import json
import re
import secrets
import tempfile
import time
import threading
from . import causes, settings, schema
from .core import InformationDB, utcnow
from .jobs import JobQueue


class Application:
    def __init__(self, database: Path, raw: Path, artifacts: Path, *, token: str, write_scope: str):
        if not token or len(token) < 24 or write_scope != 'settings':
            raise ValueError('Invalid managed service configuration')
        self.database = database
        self.processors_default = 1
        self.snapshot = None
        self.snapshot_lock = threading.RLock()
        self.snapshot_timer = None
        database.parent.mkdir(parents=True, exist_ok=True)
        if database.exists():
            with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)) as db:
                schema.require_supported_database(db)
                if schema.version(db) == schema.SCHEMA_VERSION:
                    schema.validate_structure(db)
        with InformationDB(database):
            pass

    def handle(self, method: str, path: str, query: dict, body: dict):
        cursor = query.get('cursor') if path == '/api/jobs' else None
        if cursor and cursor.startswith('s:'):
            match = re.fullmatch(r's:([0-9a-f]{32}):([0-9]{1,12})', cursor)
            if not match:
                raise ValueError('invalid cursor')
            return self._frame(int(match[2]), match[1])
        with InformationDB(self.database) as db:
            if path == '/api/status' and method == 'GET':
                return {'schemaVersion': schema.version(db.db)}
            if path == '/api/settings/processing/probe' and method == 'POST':
                db.db.execute('BEGIN IMMEDIATE')
                try:
                    original = settings.processors(db.db, fallback=self.processors_default)
                    probe = 2 if original == 1 else 1
                    settings.save_processors(db.db, probe, at=utcnow())
                    if settings.processors(db.db, fallback=self.processors_default) != probe:
                        raise RuntimeError('settings probe failed')
                finally:
                    db.db.execute('ROLLBACK')
                return {'writable': True}
            if path == '/api/settings/processing':
                if method == 'GET':
                    return {'processors': settings.processors(db.db, fallback=self.processors_default),
                            'max': settings.MAX_PROCESSORS}
                if method in {'POST', 'PUT'}:
                    value = body.get('processors')
                    if isinstance(value, str) and value.strip().isdigit():
                        value = int(value.strip())
                    return {'processors': settings.save_processors(db.db, value, at=utcnow())}
                raise ValueError('Unsupported processing settings method')
            if path == '/api/jobs' and method == 'GET':
                cursor = query.get('cursor')
                if cursor is None:
                    row_id, offset, digest = 2**63 - 1, 0, '-'
                else:
                    match = re.fullmatch(r'(-?(?:0|[1-9][0-9]{0,18})):([0-9]{1,12}):(-|[0-9a-f]{64})', cursor)
                    if not match:
                        raise ValueError('invalid cursor')
                    row_id, offset, digest = int(match[1]), int(match[2]), match[3]
                    if not -2**63 <= row_id <= 2**63-1 or (offset == 0) != (digest == '-'):
                        raise ValueError('invalid cursor')
                rows = db.db.execute('''
                    SELECT j.rowid AS cursor_rowid,j.id,j.item_id,j.stage,j.status,j.attempts,j.error,j.batch_id,
                           j.created_at,j.updated_at,j.available_at,j.result_json,
                           i.title,i.media_type,i.id IS NULL AS item_unavailable,
                           (SELECT s.error FROM stage_state s
                             WHERE s.item_id=j.item_id AND s.status='failed'
                               AND s.stage=j.stage
                               AND s.error IS NOT NULL AND s.error<>''
                             ORDER BY s.updated_at DESC LIMIT 1) AS stage_error,
                           CASE WHEN d.id IS NULL THEN 0 ELSE 1 END AS dismissed
                    FROM processing_jobs j LEFT JOIN items i ON i.id=j.item_id
                    LEFT JOIN failure_dismissals d
                           ON d.kind='job' AND d.id=j.id AND d.stamp=j.updated_at
                    WHERE j.rowid <= ? ORDER BY j.rowid DESC LIMIT 1''', (row_id,)).fetchall()
                queue = JobQueue(db)
                if cursor is not None and rows and rows[0]['cursor_rowid'] != row_id:
                    raise ValueError('stale cursor')
                if not rows:
                    if cursor is not None: raise ValueError('invalid cursor')
                    return {'chunk': '', 'recordComplete': False, 'next': None}
                jobs = []
                for row in rows:
                    job = dict(row)
                    row_id = job.pop('cursor_rowid')
                    unavailable = bool(job.pop('item_unavailable'))
                    resolved = not unavailable and queue.failure_resolved(row)
                    retryable = not unavailable and queue.retryable(row)
                    retry_blocked = None
                    if unavailable:
                        retry_blocked = 'The original item is unavailable; restore its verified record before retrying'
                    elif row['status'] == 'failed' and not resolved:
                        if not retryable:
                            retry_blocked = 'This processing stage requires its guarded runner and cannot be retried here'
                        else:
                            retryable = False
                            retry_blocked = 'Settings-write server only accepts settings mutations'
                    job.update(dismissed=bool(row['dismissed']), itemUnavailable=unavailable,
                               resolved=resolved, retryable=retryable, retryBlocked=retry_blocked,
                               cause=causes.classify(str(row['error'] or '')))
                    jobs.append(job)
                self._clear_snapshot()
                encoded = json.dumps(jobs[0], ensure_ascii=False, separators=(',', ':')).encode('utf-8')
                if len(encoded) > 512 * 1024 * 1024:
                    raise ValueError('record exceeds snapshot capacity')
                following = db.db.execute('SELECT rowid FROM processing_jobs WHERE rowid < ? ORDER BY rowid DESC LIMIT 1', (row_id,)).fetchone()
                next_cursor = f'{following[0]}:0:-' if following else None
                spool = tempfile.TemporaryFile(dir=self.database.parent)
                spool.write(encoded)
                token = secrets.token_hex(16)
                with self.snapshot_lock:
                    self.snapshot = (token, spool, len(encoded), next_cursor, time.monotonic() + 120)
                    self.snapshot_timer = threading.Timer(120, self._expire_snapshot, args=(token,))
                    self.snapshot_timer.daemon = True
                    self.snapshot_timer.start()
                return self._frame(0, token)
            raise ValueError('Unsupported operation')

    def _expire_snapshot(self, token):
        with self.snapshot_lock:
            if self.snapshot and self.snapshot[0] == token:
                self._clear_snapshot()

    def _clear_snapshot(self):
        with self.snapshot_lock:
            if self.snapshot_timer:
                self.snapshot_timer.cancel()
                self.snapshot_timer = None
            if self.snapshot:
                self.snapshot[1].close()
                self.snapshot = None

    def _frame(self, offset, expected):
        with self.snapshot_lock:
            if not self.snapshot or self.snapshot[0] != expected or time.monotonic() > self.snapshot[4]:
                if self.snapshot and self.snapshot[0] == expected:
                    self._clear_snapshot()
                raise ValueError('expired cursor')
            token, spool, size, following, deadline = self.snapshot
            if offset < 0 or offset >= size or offset % 24000:
                raise ValueError('invalid cursor')
            spool.seek(offset)
            chunk = spool.read(24000)
            end = offset + len(chunk)
            complete = end == size
            next_cursor = following if complete else f's:{token}:{end}'
            if complete:
                self._clear_snapshot()
            return {'chunk': base64.b64encode(chunk).decode('ascii'),
                    'recordComplete': complete, 'next': next_cursor}
