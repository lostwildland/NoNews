"""Explicit, drain-first migration of legacy IO model bindings."""
import json

from . import configuration, settings
from .core import transaction, utcnow


def save(db, key, value):
    db.execute('INSERT INTO app_settings(key,value,updated_at) VALUES (?,?,?) '
               'ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at',
               (key, value, utcnow()))


def roles(stage):
    return ('curator', 'editor') if stage == 'auto' else ('curator',) if stage in {'curator', 'tags'} else ('editor',) if stage == 'editor' else ()


def job_kit(db, job):
    observed = db.execute('SELECT f.freshrss_feed_id FROM entry_observations o JOIN feeds f ON f.id=o.feed_id '
                          'WHERE o.item_id=? ORDER BY o.id LIMIT 1', (job['item_id'],)).fetchone()
    live = db.execute('SELECT media_type,kit_id FROM ai_feed_settings WHERE freshrss_feed_id=?', (str(observed[0]),)).fetchone() if observed else None
    pinned = db.execute('SELECT media_type,kit_id FROM item_feed_contracts WHERE item_id=?', (job['item_id'],)).fetchone()
    if pinned and not pinned['media_type']:
        pinned = None
    contract = (live or pinned) if (job['origin'] or 'user') in {'user', 'batch'} else (pinned or live)
    media = db.execute('SELECT media_type FROM items WHERE id=?', (job['item_id'],)).fetchone()
    if media is None:
        raise configuration.ConfigurationError('Job item unavailable')
    return (contract['kit_id'] if contract else None) or media[0]


def preview(db, catalog, choices):
    rows = []
    for row in db.execute('SELECT kit_id,role,config_json FROM model_configs ORDER BY kit_id,role'):
        old = json.loads(row['config_json'])
        key = f"{old.get('provider', '')}/{old.get('model', '')}"
        role_key = f"{row['kit_id']}/{row['role']}"
        target = choices.get(role_key) or old.get('target') or choices.get(key)
        if not target and key in catalog:
            target = key
        reason = None if target in catalog else 'No explicit or exact provider/model mapping'
        rows.append({'kit': row['kit_id'], 'role': row['role'], 'old': old, 'target': target if not reason else None,
                     'basis': 'explicit choice' if key in choices or role_key in choices else 'saved target' if old.get('target') else 'exact provider/model',
                     'blocked': reason})
    by_role = {(row['kit'], row['role']): row for row in rows}
    pending = []
    for job in db.execute("SELECT * FROM processing_jobs WHERE status='pending'"):
        kit = job_kit(db, job)
        blocked = [f'{kit}/{role}' for role in roles(job['stage'])
                   if not (role == 'editor' and job['editor_target']) and not by_role.get((kit, role), {}).get('target')]
        pending.append({'id': job['id'], 'kit': kit, 'stage': job['stage'], 'blocked': blocked,
                        'editorTarget': job['editor_target']})
    return {'models': rows, 'pending': pending,
            'running': db.execute("SELECT count(*) FROM processing_jobs WHERE status='running'").fetchone()[0],
            'paused': settings._read(db, 'magpie_claims_paused') == '1',
            'evidence': json.loads(settings._read(db, 'magpie_migration_evidence') or '[]')}


def command(db, action, body):
    if action == 'pause':
        with transaction(db):
            save(db, 'magpie_claims_paused', '1')
        return {'paused': True}
    connection = configuration._record(db, 'service', body.get('serviceId'))
    choices = body.get('choices', {})
    if connection['type'] != 'magpie' or connection['stale'] or not isinstance(choices, dict) or any(
            not isinstance(key, str) or not isinstance(value, str) for key, value in choices.items()):
        raise configuration.ConfigurationError('A current Magpie directory and valid choices are required')
    if action == 'preview':
        return preview(db, connection['targets'], choices)
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
            return {'status': 'waiting', **report}
        evidence = json.loads(settings._read(db, 'magpie_migration_evidence') or '[]')
        for row in report['models']:
            if row['target'] and row['old'] != {'target': row['target']}:
                db.execute('UPDATE model_configs SET config_json=?,updated_at=? WHERE kit_id=? AND role=?',
                           (json.dumps({'target': row['target']}), utcnow(), row['kit'], row['role']))
                evidence.append({**row, 'serviceId': connection['id'], 'endpoint': connection['endpoint'], 'checkedAt': connection['checkedAt']})
        save(db, 'magpie_migration_evidence', json.dumps(evidence))
        save(db, 'magpie_migration_active', '1')
        pending = {job['id']: job for job in report['pending']}
        mapped = {(row['kit'], row['role']): row['target'] for row in report['models']}
        for job in db.execute("SELECT * FROM processing_jobs WHERE status='pending'").fetchall():
            blocked = pending[job['id']]['blocked']
            db.execute('UPDATE processing_jobs SET magpie_block_reason=? WHERE id=?',
                       ('Magpie mapping required: ' + ', '.join(blocked) if blocked else None, job['id']))
            for checkpoint in db.execute("SELECT stage,result_json FROM pipeline_stage_runs WHERE job_id=? AND item_id=? AND status!='ready' AND stage IN ('curator','editor')", (job['id'], job['item_id'])).fetchall():
                if checkpoint['stage'] == 'editor' and job['editor_target']:
                    continue
                target = mapped.get((job_kit(db, job), checkpoint['stage']))
                if target:
                    context = json.loads(checkpoint['result_json'] or '{}')
                    old = {key: context.pop(key) for key in ('provider', 'model', 'thinking_effort', 'fallback') if key in context}
                    if old:
                        context['magpie_migration'] = {'old': old, 'target': target}
                    context['requested_target'] = target
                    db.execute('UPDATE pipeline_stage_runs SET result_json=? WHERE job_id=? AND item_id=? AND stage=? AND status!=\'ready\'',
                               (json.dumps(context), job['id'], job['item_id'], checkpoint['stage']))
        save(db, 'magpie_claims_paused', '0')
        return {'status': 'applied', **preview(db, connection['targets'], choices)}
