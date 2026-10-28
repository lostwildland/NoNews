"""Explicit, drain-first migration of legacy IO model bindings."""
import json
import uuid
import base64

from . import configuration, settings
from .core import transaction, utcnow


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


def preview(db, catalog, choices):
    rows = []
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
        rows.append({'kit': row['kit_id'], 'role': row['role'], 'old': old, 'target': target if not reason else None,
                     'basis': basis,
                     'serviceId': binding['serviceId'] if binding else None,
                     'blocked': reason})
    by_role = {(row['kit'], row['role']): row for row in rows}
    pending = []
    for job in db.execute("SELECT * FROM processing_jobs WHERE status='pending'"):
        kit, refusal = job_kit(db, job) if roles(job['stage']) else (None, None)
        blocked = [refusal] if refusal else [f'{kit}/{role}' for role in roles(job['stage'])
                   if not (role == 'editor' and job['editor_target']) and not by_role.get((kit, role), {}).get('target')]
        _, binding = association(db, 'migration-job', job['id'])
        pending.append({'id': job['id'], 'kit': kit, 'stage': job['stage'], 'blocked': blocked,
                        'editorTarget': job['editor_target'], 'editorServiceId': binding['serviceId'] if binding else None})
    return {'models': rows, 'pending': pending,
            'running': db.execute("SELECT count(*) FROM processing_jobs WHERE status='running'").fetchone()[0],
            'paused': settings._read(db, 'magpie_claims_paused') == '1',
            'evidence': json.loads(settings._read(db, 'magpie_migration_evidence') or '[]')}


def report_page(db, body):
    identity = body.get('snapshotId')
    offset = body.get('offset')
    if not isinstance(identity, str) or len(identity) != 32 or any(c not in '0123456789abcdef' for c in identity) or type(offset) is not int or offset < 0:
        raise configuration.ConfigurationError('Invalid migration cursor')
    prefix = f'nonews.migration-snapshot.{identity}.'
    meta = db.execute('SELECT value FROM app_settings WHERE key=?', (prefix + 'count',)).fetchone()
    if meta is None or offset >= int(meta[0]):
        raise configuration.ConfigurationError('Invalid migration cursor')
    row = db.execute('SELECT value FROM app_settings WHERE key=?', (prefix + str(offset),)).fetchone()
    if row is None:
        raise configuration.ConfigurationError('Migration snapshot incomplete')
    return {'chunk': row[0], 'next': {'snapshotId': identity, 'offset': offset + 1} if offset + 1 < int(meta[0]) else None}


def snapshot_report(db, report):
    encoder = json.JSONEncoder(ensure_ascii=True, separators=(',', ':'))
    data = bytearray()
    identity = uuid.uuid4().hex
    prefix = f'nonews.migration-snapshot.{identity}.'
    count = 0
    with transaction(db):
        for piece in encoder.iterencode(report):
            data.extend(piece.encode('ascii'))
            while len(data) >= 48_000:
                save(db, prefix + str(count), base64.b64encode(data[:48_000]).decode('ascii'))
                del data[:48_000]
                count += 1
        if count == 0:
            return report
        if data:
            save(db, prefix + str(count), base64.b64encode(data).decode('ascii'))
            count += 1
        save(db, prefix + 'count', str(count))
    return report_page(db, {'snapshotId': identity, 'offset': 0})


def command(db, action, body):
    if action == 'pause':
        with transaction(db):
            save(db, 'magpie_claims_paused', '1')
        return {'paused': True}
    if action == 'preview' and 'snapshotId' in body:
        return report_page(db, body)
    connection = configuration._record(db, 'service', body.get('serviceId'))
    choices = body.get('choices', {})
    if connection['type'] != 'magpie' or connection['stale'] or not isinstance(choices, dict) or any(
            not isinstance(key, str) or not isinstance(value, str) for key, value in choices.items()):
        raise configuration.ConfigurationError('A current Magpie directory and valid choices are required')
    if action == 'preview':
        return snapshot_report(db, preview(db, connection['targets'], choices))
    if action != 'apply':
        raise configuration.ConfigurationError('Invalid migration action')
    with transaction(db):
        connection = configuration._record(db, 'service', body.get('serviceId'))
        if connection['stale'] or connection['type'] != 'magpie':
            raise configuration.ConfigurationError('Magpie directory is stale')
        if settings._read(db, 'magpie_claims_paused') != '1':
            raise configuration.ConfigurationError('Pause claims before migration')
        report = preview(db, connection['targets'], choices)
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
            if job['editor_target'] and pending[job['id']]['kit'] is not None:
                identity, existing = association(db, 'migration-job', job['id'])
                if existing is None:
                    configuration._store(db, 'migration-job', {'id': identity, 'jobId': job['id'],
                        'serviceId': connection['id'], 'target': job['editor_target'], 'endpoint': connection['endpoint']})
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
