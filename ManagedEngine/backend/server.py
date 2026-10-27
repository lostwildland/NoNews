"""Managed settings-scope slice of the IO Application public dispatch."""
from pathlib import Path
from contextlib import closing
import sqlite3
import base64
import hashlib
import json
import re
from . import causes, settings, schema
from .core import InformationDB, utcnow
from .jobs import JobQueue


def _job_reason(row):
    recorded = str(row['error'] or '')
    if recorded and not recorded.startswith('Processing stage failed'):
        return recorded
    return str(row['stage_error'] or '') or recorded


class Application:
    def __init__(self, database: Path, raw: Path, artifacts: Path, *, token: str, write_scope: str):
        if not token or len(token) < 24 or write_scope != 'settings':
            raise ValueError('Invalid managed service configuration')
        self.database = database
        self.processors_default = 1
        database.parent.mkdir(parents=True, exist_ok=True)
        if database.exists():
            with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)) as db:
                schema.require_supported_database(db)
                if schema.version(db) == schema.SCHEMA_VERSION:
                    schema.validate_structure(db)
        with InformationDB(database):
            pass

    def handle(self, method: str, path: str, query: dict, body: dict):
        with InformationDB(self.database) as db:
            if path == '/api/status' and method == 'GET':
                return {'schemaVersion': schema.version(db.db)}
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
                    match = re.fullmatch(r'([1-9][0-9]{0,18}):([0-9]{1,12}):(-|[0-9a-f]{64})', cursor)
                    if not match:
                        raise ValueError('invalid cursor')
                    row_id, offset, digest = int(match[1]), int(match[2]), match[3]
                    if row_id > 2**63-1 or (offset == 0) != (digest == '-'):
                        raise ValueError('invalid cursor')
                rows = db.db.execute('''
                    SELECT j.rowid AS cursor_rowid,j.id,j.item_id,j.stage,j.status,j.attempts,j.error,j.batch_id,
                           j.created_at,j.updated_at,j.available_at,j.result_json,
                           i.title,i.media_type,
                           (SELECT s.error FROM stage_state s
                             WHERE s.item_id=j.item_id AND s.status='failed'
                               AND s.error IS NOT NULL AND s.error<>''
                             ORDER BY s.updated_at DESC LIMIT 1) AS stage_error,
                           CASE WHEN d.id IS NULL THEN 0 ELSE 1 END AS dismissed
                    FROM processing_jobs j JOIN items i ON i.id=j.item_id
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
                    resolved = queue.failure_resolved(row)
                    retryable = queue.retryable(row)
                    retry_blocked = None
                    if row['status'] == 'failed' and not resolved:
                        if not retryable:
                            retry_blocked = 'This processing stage requires its guarded runner and cannot be retried here'
                        else:
                            retryable = False
                            retry_blocked = 'Settings-write server only accepts settings mutations'
                    job.update(error=_job_reason(row), dismissed=bool(row['dismissed']),
                               resolved=resolved, retryable=retryable, retryBlocked=retry_blocked,
                               cause=causes.classify(_job_reason(row)))
                    jobs.append(job)
                encoded = json.dumps(jobs[0], ensure_ascii=False, separators=(',', ':')).encode('utf-8')
                actual = hashlib.sha256(encoded).hexdigest()
                if (offset and digest != actual) or offset >= len(encoded):
                    raise ValueError('stale cursor')
                end = min(len(encoded), offset + 24000)
                complete = end == len(encoded)
                if complete:
                    following = db.db.execute('SELECT rowid FROM processing_jobs WHERE rowid < ? ORDER BY rowid DESC LIMIT 1', (row_id,)).fetchone()
                    next_cursor = f'{following[0]}:0:-' if following else None
                else:
                    next_cursor = f'{row_id}:{end}:{actual}'
                return {'chunk': base64.b64encode(encoded[offset:end]).decode('ascii'),
                        'recordComplete': complete, 'next': next_cursor}
            raise ValueError('Unsupported operation')
