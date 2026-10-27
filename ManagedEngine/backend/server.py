"""Managed settings-scope slice of the IO Application public dispatch."""
from pathlib import Path
from contextlib import closing
import sqlite3
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
                try:
                    limit = max(1, min(500, int(query.get('limit', [200])[0])))
                except ValueError:
                    limit = 200
                rows = db.db.execute('''
                    SELECT j.id,j.item_id,j.stage,j.status,j.attempts,j.error,j.batch_id,
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
                    ORDER BY j.rowid DESC LIMIT ?''', (limit,)).fetchall()
                queue = JobQueue(db)
                jobs = []
                for row in rows:
                    job = dict(row)
                    job.pop('result_json')
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
                return {'jobs': jobs}
            raise ValueError('Unsupported operation')
