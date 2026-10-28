"""Managed settings-scope slice of the IO Application public dispatch."""
from pathlib import Path
from contextlib import closing
import sqlite3
import base64
import re
import secrets
import tempfile
import time
import threading
import json
from . import causes, settings, schema, configuration, magpie_migration
from .core import InformationDB, utcnow
from .job_stream import SnapshotWriter, SnapshotTooLarge, SNAPSHOT_CAPACITY, aggregate_failed_stages_steps, text_chunks


class Application:
    def __init__(self, database: Path, raw: Path, artifacts: Path, *, token: str, write_scope: str):
        if not token or len(token) < 24 or write_scope != 'settings':
            raise ValueError('Invalid managed service configuration')
        self.database = database
        self.processors_default = 1
        self.snapshot = None
        self.snapshot_lock = threading.RLock()
        self.snapshot_timer = None
        self.preparation = None
        self.preparation_timer = None
        self.migration_lock = threading.RLock()
        self.migration_serial = threading.Lock()
        self.migration_operations = {}
        self.migration_tail = None
        self.migration_closed = False
        database.parent.mkdir(parents=True, exist_ok=True)
        if database.exists():
            with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)) as db:
                schema.require_supported_database(db)
                if schema.version(db) == schema.SCHEMA_VERSION:
                    schema.validate_structure(db)
        with InformationDB(database):
            pass

    def handle(self, method: str, path: str, query: dict, body: dict, *, response_budget=None, _queued=False):
        if method == 'POST' and path.startswith('/api/config/migration/') and (body.get('cooperative') is True or 'operationId' in body):
            return self._migration_operation(path.rsplit('/', 1)[-1], body, response_budget=response_budget)
        cursor = query.get('cursor') if path == '/api/jobs' else None
        if cursor and cursor.startswith('s:'):
            match = re.fullmatch(r's:([0-9a-f]{32}):([0-9]{1,12})', cursor)
            if not match:
                raise ValueError('invalid cursor')
            return self._frame(int(match[2]), match[1])
        if path == '/api/jobs' and method == 'GET':
            return self._jobs(query)
        if not _queued and method != 'GET' and not (path == '/api/config/migration/preview' and 'snapshotId' in body):
            with self.migration_lock:
                busy = any(not item['done'] for item in self.migration_operations.values())
                if busy:
                    pending = self._start_migration('mutation', {'method': method, 'path': path, 'query': query, 'body': body, 'response_budget': response_budget})
                    return {'_pendingMutation': pending['operationId']}
        read_only = method == 'GET' or (path == '/api/config/migration/preview' and 'snapshotId' in body)
        with InformationDB(self.database, read_only=read_only) as db:
            if path == '/api/config/services':
                return configuration.service(db.db, method, body)
            if path == '/api/config/prompts':
                return configuration.prompt(db.db, method, body)
            if path == '/api/config/history':
                return configuration.history(db.db, body)
            if path == '/api/config/copy':
                return configuration.copy_prompt(db.db, body)
            if path == '/api/config/restore':
                return configuration.restore(db.db, body)
            if path == '/api/config/refresh':
                return configuration.refresh(db.db, body)
            if path == '/api/config/references':
                return configuration.references(db.db, method, body)
            if path == '/api/config/render':
                return configuration.render(db.db, body, **({'wire_budget': response_budget} if response_budget is not None else {}))
            if path == '/api/config/bind':
                return configuration.bind(db.db, body)
            if path == '/api/config/import-legacy':
                return configuration.import_legacy(db.db, body)
            if path == '/api/config/legacy':
                return configuration.legacy(db.db, body)
            if path.startswith('/api/config/migration/'):
                return magpie_migration.command(db.db, path.rsplit('/', 1)[-1], body)
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
            raise ValueError('Unsupported operation')

    def _jobs(self, query):
        cursor = query.get('cursor')
        if cursor and cursor.startswith('p:'):
            match = re.fullmatch(r'p:([0-9a-f]{32}):([0-9]{1,12})', cursor)
            if not match:
                raise ValueError('invalid cursor')
            with self.snapshot_lock:
                state = self.preparation
                if not state or state['token'] != match[1] or state['sequence'] != int(match[2]) or time.monotonic() > state['deadline']:
                    if state and state['token'] == match[1] and time.monotonic() > state['deadline']:
                        self._clear_snapshot()
                    raise ValueError('expired cursor')
                state['deadline'] = time.monotonic() + 120
                return self._advance_preparation(state)
        if cursor is not None:
            match = re.fullmatch(r'(-?(?:0|[1-9][0-9]{0,18})):([0-9]{1,12}):(-|[0-9a-f]{64})', cursor)
            if not match or not -2**63 <= int(match[1]) <= 2**63-1 or (int(match[2]) == 0) != (match[3] == '-'):
                raise ValueError('invalid cursor')
        with self.snapshot_lock:
            self._clear_snapshot()
            state = {'token': secrets.token_hex(16), 'sequence': 0,
                     'deadline': time.monotonic() + 120, 'iterator': self._prepare_job(query)}
            self.preparation = state
            self.preparation_timer = threading.Timer(120, self._expire_preparation, args=(state['token'],))
            self.preparation_timer.daemon = True
            self.preparation_timer.start()
            return self._advance_preparation(state)

    def _advance_preparation(self, state):
        self.preparation = None
        try:
            next(state['iterator'])
        except StopIteration as result:
            self.preparation = None
            if self.preparation_timer:
                self.preparation_timer.cancel()
                self.preparation_timer = None
            return result.value
        except BaseException:
            self._clear_snapshot()
            raise
        self.preparation = state
        state['sequence'] += 1
        state['deadline'] = time.monotonic() + 120
        return {'chunk': '', 'recordComplete': False, 'next': f"p:{state['token']}:{state['sequence']}", 'preparing': True}

    def _expire_preparation(self, token):
        with self.snapshot_lock:
            state = self.preparation
            if not state or state['token'] != token:
                return
            remaining = state['deadline'] - time.monotonic()
            if remaining > 0:
                self.preparation_timer = threading.Timer(remaining, self._expire_preparation, args=(token,))
                self.preparation_timer.daemon = True
                self.preparation_timer.start()
            else:
                self._clear_snapshot()

    def close(self):
        self._clear_snapshot()
        with self.migration_lock:
            self.migration_closed = True
            operations = list(self.migration_operations.values())
            for operation in operations:
                operation['timer'].cancel()
                if not operation['done'] and operation['action'] != 'mutation':
                    operation['cancel'].set()
        for operation in operations:
            operation['thread'].join()
        for operation in operations:
            if operation.get('cleanup'):
                operation['cleanup'].join()
            self._discard_unread_migration(operation)

    def _discard_unread_migration(self, operation):
        with self.migration_lock:
            result = operation['result']
            if operation['action'] != 'preview' or operation['read'] or not isinstance(result, dict) or not result.get('snapshotId'):
                return
            operation['read'] = True
        with InformationDB(self.database) as db:
            try:
                magpie_migration.release_report(db.db, {'snapshotId': result['snapshotId']})
            except magpie_migration.SnapshotExpired:
                pass

    def _expire_migration(self, identity):
        with self.migration_lock:
            operation = self.migration_operations.get(identity)
            if not operation:
                return
            remaining = operation['deadline'] - time.monotonic()
            if remaining > 0:
                operation['timer'] = threading.Timer(remaining, self._expire_migration, args=(identity,))
                operation['timer'].daemon = True
                operation['timer'].start()
                return
            if operation['action'] != 'mutation':
                operation['cancel'].set()
        operation['thread'].join()
        if operation.get('cleanup'):
            operation['cleanup'].join()
        self._discard_unread_migration(operation)
        with self.migration_lock:
            self.migration_operations.pop(identity, None)

    def _start_migration(self, action, body):
        if self.migration_closed:
            raise magpie_migration.SnapshotExpired('Migration service stopped')
        for identity, existing in tuple(self.migration_operations.items()):
            if existing['done'] and existing['read'] and (not existing.get('cleanup') or not existing['cleanup'].is_alive()):
                existing['timer'].cancel()
                del self.migration_operations[identity]
        if len(self.migration_operations) >= 32:
            raise magpie_migration.MigrationBusy('Too many migration operations')
        if action == 'preview':
            for existing in self.migration_operations.values():
                if existing['action'] == 'preview' and not existing['done']:
                    existing['cancel'].set()
        operation = {'id': secrets.token_hex(16), 'action': action, 'cancel': threading.Event(),
                     'done': False, 'read': False, 'error': None, 'result': None,
                     'deadline': time.monotonic() + 120}
        previous = self.migration_tail
        operation['thread'] = threading.Thread(target=self._run_migration, args=(operation, dict(body), previous), daemon=True)
        operation['timer'] = threading.Timer(120, self._expire_migration, args=(operation['id'],))
        operation['timer'].daemon = True
        self.migration_operations[operation['id']] = operation
        self.migration_tail = operation['thread']
        operation['thread'].start()
        operation['timer'].start()
        return {'state': 'running', 'operationId': operation['id']}

    def _migration_operation(self, action, body, *, response_budget=None):
        if action not in {'preview', 'pause', 'apply', 'release', 'operation'}:
            raise configuration.ConfigurationError('Invalid migration operation')
        with self.migration_lock:
            if 'operationId' not in body:
                if action == 'operation':
                    raise configuration.ConfigurationError('Invalid migration operation')
                return self._start_migration(action, body)
            identity = body['operationId']
            if not isinstance(identity, str) or not re.fullmatch(r'[0-9a-f]{32}', identity):
                raise configuration.ConfigurationError('Invalid migration operation')
            operation = self.migration_operations.get(identity)
            if not operation or action != ('operation' if operation['action'] == 'mutation' else operation['action']):
                raise magpie_migration.SnapshotExpired('Migration operation expired')
            operation['deadline'] = time.monotonic() + 120
            if body.get('cancel') is True and operation['action'] not in {'apply', 'mutation'}:
                operation['cancel'].set()
                if operation['done'] and operation['action'] == 'preview':
                    if not operation['read']:
                        if not operation.get('cleanup'):
                            operation['cleanup'] = threading.Thread(target=self._discard_unread_migration, args=(operation,), daemon=True)
                            operation['cleanup'].start()
                    raise magpie_migration.SnapshotExpired('Migration operation cancelled')
            if not operation['done']:
                return {'state': 'running', 'operationId': operation['id']}
            if operation['cancel'].is_set() and operation['action'] == 'preview':
                raise magpie_migration.SnapshotExpired('Migration operation cancelled')
            operation['read'] = True
            if operation['error']:
                raise operation['error']
            if operation.get('render') and response_budget is not None:
                encoded = json.dumps({'state': 'complete', 'operationId': operation['id'], 'result': operation['result']}, separators=(',', ':'), ensure_ascii=True)
                if len(encoded) > response_budget:
                    raise configuration.RenderCapacityError('Rendered response exceeds transport capacity')
            return {'state': 'complete', 'operationId': operation['id'], 'result': operation['result']}

    def _run_migration(self, operation, body, previous):
        result = None
        try:
            if previous:
                previous.join()
            with self.migration_serial:
                if operation['cancel'].is_set():
                    raise magpie_migration.SnapshotExpired('Migration operation cancelled')
                if operation['action'] == 'mutation':
                    operation['render'] = body['path'] == '/api/config/render'
                    result = self.handle(body['method'], body['path'], body['query'], body['body'], response_budget=body.get('response_budget'), _queued=True)
                else:
                    with InformationDB(self.database) as db:
                        db.db.set_progress_handler(lambda: int(operation['cancel'].is_set()), 1000)
                        result = magpie_migration.command(db.db, operation['action'], body, operation_id=operation['id'])
                        db.db.set_progress_handler(None, 0)
                        if operation['cancel'].is_set() and operation['action'] == 'preview' and isinstance(result, dict) and result.get('snapshotId'):
                            magpie_migration.release_report(db.db, {'snapshotId': result['snapshotId']})
                            raise magpie_migration.SnapshotExpired('Migration operation cancelled')
        except Exception as error:
            if operation['cancel'].is_set():
                error = magpie_migration.SnapshotExpired('Migration operation cancelled')
            with self.migration_lock:
                operation['error'] = error
        else:
            with self.migration_lock:
                operation['result'] = result
        finally:
            with self.migration_lock:
                operation['done'] = True

    @staticmethod
    def _steps(iterator, cooperative):
        try:
            while True:
                try:
                    next(iterator)
                except StopIteration as result:
                    return result.value
                if cooperative:
                    yield None
        finally:
            iterator.close()

    def _prepare_job(self, query):
        with InformationDB(self.database, read_only=True, cross_thread=True) as db:
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
            db.db.execute('BEGIN')
            rows = db.db.execute('''
                SELECT j.rowid AS cursor_rowid,NULL AS id,NULL AS item_id,NULL AS stage,NULL AS status,NULL AS attempts,
                       NULL AS error, NULL AS batch_id, NULL AS created_at,NULL AS updated_at,NULL AS available_at,
                       CASE WHEN j.stage IN ('auto','acquisition','curator','editor','tags','maintenance','media','historical_curator','scoring') THEN j.stage END AS semantic_stage,
                       j.status='failed' AS is_failed,
                       NULL AS result_json,
                       j.result_json IS NOT NULL AS has_result,
                       NULL AS title,NULL AS media_type,i.rowid AS item_rowid,i.id IS NULL AS item_unavailable,
                       (SELECT s.rowid FROM stage_state s
                         WHERE s.item_id=j.item_id AND s.status='failed'
                           AND s.stage=j.stage
                         ORDER BY s.updated_at DESC LIMIT 1) AS stage_rowid,
                       CASE WHEN d.id IS NULL THEN 0 ELSE 1 END AS dismissed
                FROM processing_jobs j LEFT JOIN items i ON i.id=j.item_id
                LEFT JOIN failure_dismissals d
                       ON d.kind='job' AND d.id=j.id AND d.stamp=j.updated_at
                WHERE j.rowid <= ? ORDER BY j.rowid DESC LIMIT 1''', (row_id,)).fetchall()
            if cursor is not None and rows and rows[0]['cursor_rowid'] != row_id:
                raise ValueError('stale cursor')
            if not rows:
                if cursor is not None: raise ValueError('invalid cursor')
                return {'chunk': '', 'recordComplete': False, 'next': None}
            jobs = []
            for row in rows:
                job = dict(row)
                row_id = job.pop('cursor_rowid')
                has_result = job.pop('has_result')
                stage = job.pop('semantic_stage')
                failed = bool(job.pop('is_failed'))
                item_rowid = job.pop('item_rowid')
                stage_rowid = job.pop('stage_rowid')
                if stage_rowid is not None:
                    stage_kind = db.db.execute('SELECT typeof(error) FROM stage_state WHERE rowid=?', (stage_rowid,)).fetchone()[0]
                    if stage_kind == 'null':
                        stage_rowid = None
                    elif stage_kind == 'text':
                        with db.db.blobopen('stage_state', 'error', stage_rowid, readonly=True) as error_blob:
                            if len(error_blob) == 0:
                                stage_rowid = None
                job['stage_error'] = None
                columns = {name: ('processing_jobs', name, row_id) for name in ('id', 'item_id', 'stage', 'status', 'attempts', 'updated_at', 'error', 'batch_id', 'created_at', 'available_at', 'result_json')}
                columns.update(title=('items', 'title', item_rowid), media_type=('items', 'media_type', item_rowid), stage_error=('stage_state', 'error', stage_rowid))
                kinds = {}
                raw_size = 0
                utf8_database = db.db.execute('PRAGMA encoding').fetchone()[0] == 'UTF-8'
                for name, (table, column, source_rowid) in columns.items():
                    if source_rowid is None:
                        kinds[name] = 'null'
                        continue
                    kind = db.db.execute(f'SELECT typeof({column}) FROM {table} WHERE rowid=?', (source_rowid,)).fetchone()[0]
                    kinds[name] = kind
                    if kind == 'blob':
                        raise TypeError('unsupported job value')
                    if kind == 'text':
                        with db.db.blobopen(table, column, source_rowid, readonly=True) as blob:
                            raw_size += len(blob) if utf8_database else (len(blob) + 1) // 2
                        if raw_size > SNAPSHOT_CAPACITY:
                            raise SnapshotTooLarge('record exceeds snapshot capacity')
                cooperative = raw_size >= 262144
                if cooperative:
                    yield None
                unavailable = bool(job.pop('item_unavailable'))
                if unavailable or not failed:
                    resolved = False
                elif stage == 'auto':
                    if kinds['result_json'] == 'text':
                        with closing(text_chunks(db.db, 'processing_jobs', 'result_json', row_id)) as chunks:
                            failed_stages = yield from self._steps(aggregate_failed_stages_steps(chunks, self.database.parent), cooperative)
                    else:
                        failed_stages = ()
                    resolved = bool(failed_stages) and all(self._resolved_job(db.db, row_id, part) for part in failed_stages)
                else:
                    resolved = self._resolved_job(db.db, row_id, stage)
                retryable = not unavailable and failed and stage in {'auto', 'acquisition', 'curator', 'editor', 'tags', 'maintenance', 'media'} and not resolved
                retry_blocked = None
                if unavailable:
                    retry_blocked = 'The original item is unavailable; restore its verified record before retrying'
                elif failed and not resolved:
                    if not retryable:
                        retry_blocked = 'This processing stage requires its guarded runner and cannot be retried here'
                    else:
                        retryable = False
                        retry_blocked = 'Settings-write server only accepts settings mutations'
                if kinds['error'] == 'text':
                    with closing(text_chunks(db.db, 'processing_jobs', 'error', row_id)) as chunks:
                        cause = yield from self._steps(causes.classify_chunks_steps(chunks), cooperative)
                else:
                    cause = causes.classify(db.db.execute('SELECT error FROM processing_jobs WHERE rowid=?', (row_id,)).fetchone()[0])
                job.update(dismissed=bool(row['dismissed']), itemUnavailable=unavailable,
                           resolved=resolved, retryable=retryable, retryBlocked=retry_blocked, cause=cause)
                jobs.append(job)
            following = db.db.execute('SELECT rowid FROM processing_jobs WHERE rowid < ? ORDER BY rowid DESC LIMIT 1', (row_id,)).fetchone()
            next_cursor = f'{following[0]}:0:-' if following else None
            spool = tempfile.TemporaryFile(dir=self.database.parent)
            try:
                writer = SnapshotWriter(spool)
                writer.write(b'{')
                for index, (key, value) in enumerate(jobs[0].items()):
                    if index:
                        writer.write(b',')
                    writer.value(key)
                    writer.write(b':')
                    if key == 'result_json' and has_result and stage != 'auto':
                        yield from self._steps(writer.text_column_steps(db.db, 'processing_jobs', 'result_json', row_id), cooperative)
                    elif key in columns and columns[key][2] is not None:
                        table, column, source_rowid = columns[key]
                        kind = kinds[key]
                        if kind == 'null':
                            writer.value(None)
                        elif kind == 'text':
                            yield from self._steps(writer.text_column_steps(db.db, table, column, source_rowid), cooperative)
                        else:
                            writer.value(db.db.execute(f'SELECT {column} FROM {table} WHERE rowid=?', (source_rowid,)).fetchone()[0])
                    else:
                        writer.value(value)
                writer.write(b'}')
                db.db.execute('COMMIT')
            except BaseException:
                spool.close()
                raise
            try:
                token = secrets.token_hex(16)
                with self.snapshot_lock:
                    self.snapshot = (token, spool, writer.size, next_cursor, time.monotonic() + 120)
                    self.snapshot_timer = threading.Timer(120, self._expire_snapshot, args=(token,))
                    self.snapshot_timer.daemon = True
                    self.snapshot_timer.start()
            except BaseException:
                self._clear_snapshot()
                spool.close()
                raise
            return self._frame(0, token)

    @staticmethod
    def _resolved_job(db, row_id, stage):
        if stage in (None, 'media'):
            return False
        item = '(SELECT item_id FROM processing_jobs WHERE rowid=?)'
        stamp = '(SELECT updated_at FROM processing_jobs WHERE rowid=?)'
        if stage == 'historical_curator':
            return bool(db.execute("SELECT 1 FROM processing_jobs j "
                "JOIN pipeline_stage_runs p ON p.job_id=j.id AND p.item_id=j.item_id AND p.stage='curator' AND p.status='ready' "
                "JOIN curator_runs c ON c.id=json_extract(p.result_json,'$.run_id') AND c.item_id=j.item_id AND c.status='succeeded' AND c.score BETWEEN 0 AND 10 "
                f"WHERE j.item_id={item} AND j.stage='historical_curator' AND j.status='succeeded' "
                f"AND j.updated_at>{stamp} AND p.updated_at>{stamp} AND c.finished_at>{stamp} LIMIT 1",
                (row_id, row_id, row_id, row_id)).fetchone())
        successes = {'scoring': ("pipeline_stage_runs", "stage='scoring' AND status='ready'", 'updated_at'),
                     'acquisition': ("pipeline_stage_runs", "stage='acquisition' AND status='ready'", 'updated_at'),
                     'curator': ("curator_runs", "status='succeeded'", 'finished_at'),
                     'editor': ("editor_drafts", '1', 'created_at'),
                     'maintenance': ("pipeline_stage_runs", "stage='maintenance' AND status='ready'", 'updated_at')}
        if stage not in successes:
            return False
        if db.execute(f"SELECT 1 FROM stage_state WHERE item_id={item} AND stage=? AND status='failed' AND updated_at<={stamp}",
                      (row_id, stage, row_id)).fetchone():
            return False
        table, condition, time_column = successes[stage]
        return bool(db.execute(f"SELECT 1 FROM {table} WHERE item_id={item} AND {condition} AND {time_column}>{stamp} LIMIT 1", (row_id, row_id)).fetchone())

    def _expire_snapshot(self, token):
        with self.snapshot_lock:
            if not self.snapshot or self.snapshot[0] != token:
                return
            remaining = self.snapshot[4] - time.monotonic()
            if remaining > 0:
                self.snapshot_timer = threading.Timer(remaining, self._expire_snapshot, args=(token,))
                self.snapshot_timer.daemon = True
                self.snapshot_timer.start()
            else:
                self._clear_snapshot()

    def _clear_snapshot(self):
        with self.snapshot_lock:
            if self.preparation_timer:
                self.preparation_timer.cancel()
                self.preparation_timer = None
            if self.preparation:
                iterator = self.preparation['iterator']
                self.preparation = None
                iterator.close()
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
            self.snapshot = (token, spool, size, following, time.monotonic() + 120)
            try:
                spool.seek(offset)
                chunk = spool.read(24000)
            except (OSError, ValueError):
                self._clear_snapshot()
                raise
            end = offset + len(chunk)
            complete = end == size
            next_cursor = following if complete else f's:{token}:{end}'
            if complete:
                self._clear_snapshot()
            return {'chunk': base64.b64encode(chunk).decode('ascii'),
                    'recordComplete': complete, 'next': next_cursor}
