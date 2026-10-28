"""Explicit, drain-first migration of legacy IO model bindings."""
import json
import uuid
import base64
import re
import hashlib
import hmac

from . import configuration, settings
from .core import transaction, utcnow
from .job_stream import text_chunks

SNAPSHOT_KEEP = 2


class StagedRows:
    def __init__(self, db, table):
        self.db, self.table = db, table

    def __iter__(self):
        for row in self.db.execute(f'SELECT payload FROM {self.table} ORDER BY sequence'):
            yield json.loads(row[0])


class EvidenceRows:
    def __init__(self, db):
        self.db = db

    def __iter__(self):
        row = self.db.execute("SELECT rowid FROM app_settings WHERE key='magpie_migration_evidence'").fetchone()
        if row is None:
            return
        with self.db.blobopen('app_settings', 'value', row[0], readonly=True) as blob:
            if len(blob) == 0:
                return
        phase, depth, quoted, escaped, item = 'start', 0, False, False, []
        for chunk in text_chunks(self.db, 'app_settings', 'value', row[0]):
            for char in chunk:
                if phase == 'start':
                    if char in ' \t\r\n':
                        continue
                    if char != '[':
                        raise configuration.ConfigurationError('Invalid migration evidence')
                    phase = 'first'
                    continue
                if phase == 'done':
                    if char not in ' \t\r\n':
                        raise configuration.ConfigurationError('Invalid migration evidence')
                    continue
                if phase in {'first', 'next'} and not item and char in ' \t\r\n':
                    continue
                if not quoted and depth == 0 and char in ',]':
                    raw = ''.join(item).strip(' \t\r\n')
                    if raw:
                        try:
                            yield json.loads(raw)
                        except ValueError as error:
                            raise configuration.ConfigurationError('Invalid migration evidence') from error
                    elif phase != 'first' or char != ']':
                        raise configuration.ConfigurationError('Invalid migration evidence')
                    item = []
                    phase = 'next' if char == ',' else 'done'
                    continue
                item.append(char)
                if quoted:
                    if escaped:
                        escaped = False
                    elif char == '\\':
                        escaped = True
                    elif char == '"':
                        quoted = False
                elif char == '"':
                    quoted = True
                elif char in '[{':
                    depth += 1
                elif char in ']}':
                    depth -= 1
                    if depth < 0:
                        raise configuration.ConfigurationError('Invalid migration evidence')
                phase = 'value'
        if phase != 'done':
            raise configuration.ConfigurationError('Invalid migration evidence')


class SnapshotExpired(ValueError):
    code = 'snapshot_expired'


def save(db, key, value):
    db.execute('INSERT INTO app_settings(key,value,updated_at) VALUES (?,?,?) '
               'ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at',
               (key, value, utcnow()))


def roles(stage):
    return ('curator', 'editor') if stage == 'auto' else ('curator',) if stage in {'curator', 'tags'} else ('editor',) if stage == 'editor' else ()


def association(db, kind, key):
    identity = uuid.uuid5(uuid.NAMESPACE_URL, key).hex
    row = db.execute('SELECT value FROM app_settings WHERE key=?', (f'nonews.{kind}.{identity}',)).fetchone()
    return (identity, json.loads(row[0]) if row else None)


def job_kit(db, job):
    observed = db.execute('SELECT f.freshrss_feed_id FROM entry_observations o JOIN feeds f ON f.id=o.feed_id '
                          'WHERE o.item_id=? ORDER BY o.id LIMIT 1', (job['item_id'],)).fetchone()
    live = db.execute('SELECT media_type,kit_id FROM ai_feed_settings WHERE freshrss_feed_id=?', (str(observed[0]),)).fetchone() if observed else None
    pinned = db.execute('SELECT media_type,kit_id FROM item_feed_contracts WHERE item_id=?', (job['item_id'],)).fetchone()
    if pinned and not pinned['media_type']:
        pinned = None
    media = db.execute('SELECT media_type FROM items WHERE id=?', (job['item_id'],)).fetchone()
    if media is None:
        raise configuration.ConfigurationError('Job item unavailable')
    adopt = (job['origin'] or 'user') in {'user', 'batch'}
    if adopt and live and live['media_type']:
        contract = live
    else:
        contract = pinned or live
    if contract and contract['media_type'] and contract['media_type'] != media[0]:
        return None, 'Media mismatch: ' + str(contract['media_type']) + ' / ' + str(media[0])
    kit = contract['kit_id'] if contract else None
    if kit:
        row = db.execute('SELECT content_type,content_types_json FROM ai_kits WHERE id=?', (kit,)).fetchone()
        if row is None:
            return None, 'Kit unavailable: ' + str(kit)
        try:
            declared = json.loads(row['content_types_json'] or 'null')
        except (TypeError, ValueError):
            declared = None
        types = [str(item) for item in declared if str(item or '') in {'news', 'paper', 'newsletter', 'podcast', 'video'}] if isinstance(declared, list) else []
        if not types:
            types = [row['content_type']]
        if media[0] not in types:
            return None, 'Kit incompatible: ' + str(kit)
    return kit or media[0], None


def preview(db, catalog, choices, service_id, editor_services, *, staged=False):
    if staged:
        db.execute('CREATE TEMP TABLE migration_preview_models(sequence INTEGER PRIMARY KEY, kit TEXT, role TEXT, target TEXT, payload TEXT)')
        db.execute('CREATE INDEX migration_preview_lookup ON migration_preview_models(kit,role)')
        db.execute('CREATE TEMP TABLE migration_preview_pending(sequence INTEGER PRIMARY KEY, job_id TEXT, payload TEXT)')
    rows = [] if not staged else None
    for row in db.execute('SELECT kit_id,role,config_json FROM model_configs ORDER BY kit_id,role'):
        raw = json.loads(row['config_json'])
        if not isinstance(raw, dict):
            raise configuration.ConfigurationError('Unsupported legacy model configuration')
        allowed = {'provider', 'model', 'thinking_effort', 'fallback', 'target'}
        unsupported = bool(set(raw) - allowed) or isinstance(raw.get('fallback'), (dict, list))
        old = {key: value for key, value in raw.items() if key in allowed and not isinstance(value, (dict, list))}
        key = f"{old.get('provider', '')}/{old.get('model', '')}"
        role_key = f"{row['kit_id']}/{row['role']}"
        if role_key in choices:
            target, basis = choices[role_key], 'explicit choice'
        elif key in choices:
            target, basis = choices[key], 'explicit choice'
        elif old.get('target'):
            target, basis = old['target'], 'saved target'
        else:
            target, basis = (key if key in catalog else None), 'exact provider/model'
        reason = 'Unsupported legacy fields require review' if unsupported else None if target in catalog else 'No explicit or exact provider/model mapping'
        _, binding = association(db, 'migration-binding', role_key)
        value = {'kit': row['kit_id'], 'role': row['role'], 'old': old, 'target': target if not reason else None,
                 'basis': basis, 'serviceId': binding['serviceId'] if binding else None, 'blocked': reason}
        if staged:
            db.execute('INSERT INTO migration_preview_models(kit,role,target,payload) VALUES (?,?,?,?)',
                       (value['kit'], value['role'], value['target'], json.dumps(value, ensure_ascii=True, separators=(',', ':'))))
        else:
            rows.append(value)
    by_role = {(row['kit'], row['role']): row for row in rows} if not staged else None
    pending = [] if not staged else None
    unseen_editor_jobs = set(editor_services)
    for job in db.execute("SELECT * FROM processing_jobs WHERE status='pending'"):
        kit, refusal = job_kit(db, job) if roles(job['stage']) else (None, None)
        def mapped(role):
            if staged:
                row = db.execute('SELECT target FROM migration_preview_models WHERE kit=? AND role=?', (kit, role)).fetchone()
                return row[0] if row else None
            return by_role.get((kit, role), {}).get('target')
        blocked = [refusal] if refusal else [f'{kit}/{role}' for role in roles(job['stage'])
                   if not (role == 'editor' and job['editor_target']) and not mapped(role)]
        _, binding = association(db, 'migration-job', job['id'])
        proposed = editor_services.get(job['id'])
        if job['editor_target']:
            unseen_editor_jobs.discard(job['id'])
            if proposed is not None:
                chosen = configuration._record(db, 'service', proposed)
                if chosen['type'] != 'magpie':
                    raise configuration.ConfigurationError('Pinned Editor service must be Magpie')
            if binding and (binding.get('target') != job['editor_target'] or (proposed is not None and proposed != binding.get('serviceId'))):
                blocked.append('Existing Editor association conflicts with this proposal')
            elif binding:
                try:
                    known = configuration._record(db, 'service', binding.get('serviceId'))
                    if known['type'] != 'magpie' or known['endpoint'] != binding.get('endpoint'):
                        blocked.append('Existing Editor gateway is unavailable or changed')
                except configuration.ConfigurationError:
                    blocked.append('Existing Editor gateway is unavailable or changed')
            elif not binding and proposed is None:
                blocked.append('Editor service association required')
        value = {'id': job['id'], 'kit': kit, 'stage': job['stage'], 'blocked': blocked,
                 'editorTarget': job['editor_target'], 'editorServiceId': binding.get('serviceId') if binding else None,
                 'proposedEditorServiceId': (proposed or (binding.get('serviceId') if binding else service_id)) if job['editor_target'] else None,
                 'editorAssociationExplicit': bool(binding or proposed)}
        if staged:
            db.execute('INSERT INTO migration_preview_pending(job_id,payload) VALUES (?,?)',
                       (value['id'], json.dumps(value, ensure_ascii=True, separators=(',', ':'))))
        else:
            pending.append(value)
    if unseen_editor_jobs:
        raise configuration.ConfigurationError('Pinned Editor job is unavailable')
    return {'models': StagedRows(db, 'migration_preview_models') if staged else rows,
            'pending': StagedRows(db, 'migration_preview_pending') if staged else pending,
            'running': db.execute("SELECT count(*) FROM processing_jobs WHERE status='running'").fetchone()[0],
            'paused': settings._read(db, 'magpie_claims_paused') == '1',
            'evidence': EvidenceRows(db) if staged else json.loads(settings._read(db, 'magpie_migration_evidence') or '[]')}


def report_page(db, body):
    identity = body.get('snapshotId')
    offset = body.get('offset')
    if not isinstance(identity, str) or len(identity) != 32 or any(c not in '0123456789abcdef' for c in identity) or type(offset) is not int or offset < 0:
        raise configuration.ConfigurationError('Invalid migration cursor')
    prefix = f'nonews.migration-snapshot.{identity}.'
    meta = db.execute('SELECT value FROM app_settings WHERE key=?', (prefix + 'count',)).fetchone()
    if meta is None:
        raise SnapshotExpired('Migration report expired')
    if offset >= int(meta[0]):
        raise configuration.ConfigurationError('Invalid migration cursor')
    row = db.execute('SELECT value FROM app_settings WHERE key=?', (prefix + str(offset),)).fetchone()
    if row is None:
        raise configuration.ConfigurationError('Migration snapshot incomplete')
    return {'snapshotId': identity, 'chunk': row[0], 'next': {'snapshotId': identity, 'offset': offset + 1} if offset + 1 < int(meta[0]) else None}


def release_report(db, body):
    identity = body.get('snapshotId')
    if not isinstance(identity, str) or not re.fullmatch(r'[0-9a-f]{32}', identity):
        raise configuration.ConfigurationError('Invalid migration cursor')
    prefix = f'nonews.migration-snapshot.{identity}.'
    with transaction(db):
        if db.execute('SELECT 1 FROM app_settings WHERE key=?', (prefix + 'count',)).fetchone() is None:
            raise SnapshotExpired('Migration report expired')
        db.execute('DELETE FROM app_settings WHERE key=? OR (key>=? AND key<?)',
                   (prefix + 'count', prefix + '0', prefix + ':'))
    return {'released': True}


def snapshot_report(db, report):
    encoder = json.JSONEncoder(ensure_ascii=True, separators=(',', ':'))
    data = bytearray()
    identity = uuid.uuid4().hex
    prefix = f'nonews.migration-snapshot.{identity}.'
    count = 0
    def pieces():
        yield '{'
        for index, (key, value) in enumerate(report.items()):
            if index:
                yield ','
            yield json.dumps(key, ensure_ascii=True) + ':'
            if key in {'models', 'pending', 'evidence'}:
                yield '['
                for position, item in enumerate(value):
                    if position:
                        yield ','
                    yield from encoder.iterencode(item)
                yield ']'
            else:
                yield from encoder.iterencode(value)
        yield '}'
    with transaction(db):
        for piece in pieces():
            for start in range(0, len(piece), 16_000):
                part = piece[start:start + 16_000].encode('ascii')
                while part:
                    length = min(48_000 - len(data), len(part))
                    data.extend(part[:length])
                    part = part[length:]
                    if len(data) == 48_000:
                        save(db, prefix + str(count), base64.b64encode(data).decode('ascii'))
                        data.clear()
                        count += 1
        if count == 0:
            return json.loads(data)
        if data:
            save(db, prefix + str(count), base64.b64encode(data).decode('ascii'))
            count += 1
        save(db, prefix + 'count', str(count))
        kept = 0
        roots = db.execute("SELECT key FROM app_settings WHERE key>=? AND key<? AND key LIKE '%.count' ORDER BY rowid DESC",
                           ('nonews.migration-snapshot.', 'nonews.migration-snapshot/'))
        for row in roots:
            key = row[0]
            if not re.fullmatch(r'nonews\.migration-snapshot\.[0-9a-f]{32}\.count', key):
                continue
            kept += 1
            if kept <= SNAPSHOT_KEEP:
                continue
            old_prefix = key[:-5]
            db.execute('DELETE FROM app_settings WHERE key=? OR (key>=? AND key<?)',
                       (key, old_prefix + '0', old_prefix + ':'))
    return report_page(db, {'snapshotId': identity, 'offset': 0})


def editor_review_digest(db, connection, choices, editor_services, report):
    services = {identity: configuration._record(db, 'service', identity)['endpoint'] for identity in editor_services.values()}
    if isinstance(report['pending'], StagedRows):
        pending = (json.loads(row[0]) for row in db.execute('SELECT payload FROM migration_preview_pending ORDER BY job_id'))
    else:
        pending = iter(sorted(report['pending'], key=lambda row: row['id']))
    jobs = ({key: row[key] for key in ('id', 'kit', 'blocked', 'editorTarget', 'editorServiceId', 'proposedEditorServiceId')}
            for row in pending if row['editorTarget'])
    payload = {'serviceId': connection['id'], 'endpoint': connection['endpoint'], 'checkedAt': connection['checkedAt'],
               'targets': connection['targets'], 'choices': choices, 'models': report['models'],
               'editorServices': editor_services, 'services': services, 'jobs': jobs}
    encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    digest = hashlib.sha256()
    digest.update(b'{')
    for index, key in enumerate(sorted(payload)):
        if index:
            digest.update(b',')
        digest.update(json.dumps(key, ensure_ascii=True).encode('ascii') + b':')
        if key in {'models', 'jobs'}:
            digest.update(b'[')
            for position, item in enumerate(payload[key]):
                if position:
                    digest.update(b',')
                for piece in encoder.iterencode(item):
                    digest.update(piece.encode('ascii'))
            digest.update(b']')
        else:
            for piece in encoder.iterencode(payload[key]):
                digest.update(piece.encode('ascii'))
    digest.update(b'}')
    return digest.hexdigest()


def command(db, action, body):
    if action == 'pause':
        with transaction(db):
            save(db, 'magpie_claims_paused', '1')
        return {'paused': True}
    if action == 'preview' and 'snapshotId' in body:
        return report_page(db, body)
    if action == 'release':
        return release_report(db, body)
    connection = configuration._record(db, 'service', body.get('serviceId'))
    choices = body.get('choices', {})
    editor_services = body.get('editorServices', {})
    if connection['type'] != 'magpie' or connection['stale'] or not isinstance(choices, dict) or any(
            not isinstance(key, str) or not isinstance(value, str) for key, value in choices.items()) or not isinstance(editor_services, dict) or any(
            not isinstance(key, str) or not isinstance(value, str) for key, value in editor_services.items()):
        raise configuration.ConfigurationError('A current Magpie directory and valid choices are required')
    if action == 'preview':
        db.execute('PRAGMA temp_store=FILE')
        with transaction(db):
            connection = configuration._record(db, 'service', body.get('serviceId'))
            if connection['stale'] or connection['type'] != 'magpie':
                raise configuration.ConfigurationError('Magpie directory is stale')
            report = preview(db, connection['targets'], choices, connection['id'], editor_services, staged=True)
            receipt = {'token': uuid.uuid4().hex,
                       'digest': editor_review_digest(db, connection, choices, editor_services, report)} if editor_services else {}
            save(db, 'nonews.migration-editor-review', json.dumps(receipt))
            if receipt:
                report['editorReviewToken'] = receipt['token']
            return snapshot_report(db, report)
    if action != 'apply':
        raise configuration.ConfigurationError('Invalid migration action')
    with transaction(db):
        connection = configuration._record(db, 'service', body.get('serviceId'))
        if connection['stale'] or connection['type'] != 'magpie':
            raise configuration.ConfigurationError('Magpie directory is stale')
        if settings._read(db, 'magpie_claims_paused') != '1':
            raise configuration.ConfigurationError('Pause claims before migration')
        report = preview(db, connection['targets'], choices, connection['id'], editor_services)
        if editor_services:
            receipt = json.loads(settings._read(db, 'nonews.migration-editor-review') or '{}')
            supplied = body.get('reviewToken')
            digest = editor_review_digest(db, connection, choices, editor_services, report)
            if not isinstance(supplied, str) or not isinstance(receipt.get('token'), str) or not hmac.compare_digest(supplied, receipt['token']) or receipt.get('digest') != digest:
                raise configuration.ConfigurationError('Review pinned Editor associations again')
        if report['running']:
            return {'status': 'waiting', 'running': report['running'], 'paused': True}
        evidence = json.loads(settings._read(db, 'magpie_migration_evidence') or '[]')
        for row in report['models']:
            if row['target']:
                identity, prior_binding = association(db, 'migration-binding', f"{row['kit']}/{row['role']}")
                binding = {'id': identity, 'kit': row['kit'], 'role': row['role'],
                           'serviceId': connection['id'], 'target': row['target'], 'endpoint': connection['endpoint']}
            if row['target'] and row['old'] != {'target': row['target']}:
                db.execute('UPDATE model_configs SET config_json=?,updated_at=? WHERE kit_id=? AND role=?',
                           (json.dumps({'target': row['target']}), utcnow(), row['kit'], row['role']))
            if row['target'] and (row['old'] != {'target': row['target']} or prior_binding != binding):
                evidence.append({**row, 'serviceId': connection['id'], 'endpoint': connection['endpoint'], 'checkedAt': connection['checkedAt']})
            if row['target']:
                configuration._store(db, 'migration-binding', binding)
        save(db, 'magpie_migration_evidence', json.dumps(evidence))
        save(db, 'magpie_migration_active', '1')
        pending = {job['id']: job for job in report['pending']}
        mapped = {(row['kit'], row['role']): row['target'] for row in report['models']}
        for job in db.execute("SELECT * FROM processing_jobs WHERE status='pending'").fetchall():
            if not roles(job['stage']):
                continue
            blocked = pending[job['id']]['blocked']
            if job['editor_target'] and pending[job['id']]['kit'] is not None and job['id'] in editor_services:
                identity, existing = association(db, 'migration-job', job['id'])
                if existing is None:
                    selected = configuration._record(db, 'service', editor_services[job['id']])
                    configuration._store(db, 'migration-job', {'id': identity, 'jobId': job['id'],
                        'serviceId': selected['id'], 'target': job['editor_target'], 'endpoint': selected['endpoint']})
            db.execute('UPDATE processing_jobs SET magpie_block_reason=? WHERE id=?',
                       ('Magpie mapping required: ' + ', '.join(blocked) if blocked else None, job['id']))
            for checkpoint in db.execute("SELECT stage,result_json FROM pipeline_stage_runs WHERE job_id=? AND item_id=? AND status!='ready' AND stage IN ('curator','editor')", (job['id'], job['item_id'])).fetchall():
                if checkpoint['stage'] == 'editor' and job['editor_target']:
                    continue
                kit, refusal = job_kit(db, job)
                target = None if refusal else mapped.get((kit, checkpoint['stage']))
                if target:
                    context = json.loads(checkpoint['result_json'] or '{}')
                    old = {key: context.pop(key) for key in ('provider', 'model', 'thinking_effort', 'fallback') if key in context}
                    if old:
                        context['magpie_migration'] = {'old': old, 'target': target}
                    context['requested_target'] = target
                    db.execute('UPDATE pipeline_stage_runs SET result_json=? WHERE job_id=? AND item_id=? AND stage=? AND status!=\'ready\'',
                               (json.dumps(context), job['id'], job['item_id'], checkpoint['stage']))
        save(db, 'magpie_claims_paused', '0')
        return {'status': 'applied', 'running': 0, 'paused': False}
