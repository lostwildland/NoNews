"""User-owned configuration; prompt text versions retain IO's history table."""
import json
import re
import uuid
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlsplit, urlunsplit

from .core import transaction, utcnow


class ConfigurationError(ValueError):
    code = 'invalid_configuration'


class PlaceholderError(ConfigurationError):
    def __init__(self, names):
        self.names = names
        super().__init__('Unavailable prompt placeholder')


def _record(db, kind, identity):
    if not isinstance(identity, str) or len(identity) != 32 or any(c not in '0123456789abcdef' for c in identity):
        raise ConfigurationError('Invalid identity')
    row = db.execute('SELECT value FROM app_settings WHERE key=?', (f'nonews.{kind}.{identity}',)).fetchone()
    if row is None:
        raise ConfigurationError('Configuration not found')
    value = json.loads(row[0])
    if kind == 'service' and value.get('checkedAt'):
        try:
            value['stale'] = bool(value.get('error')) or (datetime.now(timezone.utc) - datetime.fromisoformat(value['checkedAt'])).total_seconds() > 300
        except (TypeError, ValueError):
            value['stale'] = True
    return value


def _store(db, kind, value):
    db.execute('INSERT INTO app_settings(key,value,updated_at) VALUES (?,?,?) '
               'ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at',
               (f"nonews.{kind}.{value['id']}", json.dumps(value, ensure_ascii=False), utcnow()))


def _required(value, maximum=512):
    if not isinstance(value, str) or not value.strip() or len(value.encode('utf-8')) > maximum:
        raise ConfigurationError('Invalid configuration value')
    return value


def service(db, method, body):
    if method == 'GET':
        if 'id' not in body:
            return _list(db, 'service', body)
        return _record(db, 'service', body.get('id'))
    if method == 'DELETE':
        value = _record(db, 'service', body.get('id'))
        with transaction(db):
            if any(item['serviceId'] == value['id'] for item in _records(db, 'prompt')):
                raise ConfigurationError('Service is in use')
            db.execute('DELETE FROM app_settings WHERE key=?', (f"nonews.service.{value['id']}",))
        return {'deleted': True}
    if set(body) - {'id', 'name', 'type', 'endpoint', 'targets', 'checkedAt', 'stale', 'error'}:
        raise ConfigurationError('Invalid service fields')
    identity = body.get('id')
    prior = _record(db, 'service', identity) if identity is not None else None
    name = _required(body.get('name'))
    kind = body.get('type')
    if kind not in {'magpie', 'openai-compatible'}:
        raise ConfigurationError('Unsupported service')
    endpoint = _required(body.get('endpoint'), 2048)
    try:
        parsed = urlsplit(endpoint.strip())
        if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ConfigurationError('Invalid endpoint')
        parsed.port
        if kind == 'openai-compatible' and parsed.scheme != 'https' and parsed.hostname not in {'localhost', '127.0.0.1', '::1'}:
            raise ConfigurationError('Bearer credentials require HTTPS')
    except ValueError as error:
        raise ConfigurationError('Invalid endpoint') from error
    path = parsed.path.rstrip('/')
    if path.endswith('/v1'):
        path = path[:-3]
    value = {'id': identity or uuid.uuid4().hex, 'name': name, 'type': kind,
             'endpoint': urlunsplit((parsed.scheme, parsed.netloc, path, '', ''))}
    if prior and prior['endpoint'] == value['endpoint'] and prior['type'] == kind:
        value.update({key: prior.get(key) for key in ('targets', 'checkedAt', 'stale', 'error')})
    else:
        value.update({'targets': [], 'checkedAt': None, 'stale': True, 'error': None})
    _store(db, 'service', value)
    return value


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def refresh(db, body):
    value = _record(db, 'service', body.get('id'))
    headers = {}
    if value['type'] == 'openai-compatible':
        secret = _required(body.get('credential'), 8192)
        if '\n' in secret or '\r' in secret:
            raise ConfigurationError('Invalid credential')
        headers['Authorization'] = 'Bearer ' + secret
    try:
        request = Request(value['endpoint'] + '/v1/models', headers=headers)
        with build_opener(_NoRedirect).open(request, timeout=5) as response:
            raw = response.read(1_048_577)
        if len(raw) > 1_048_576:
            raise ValueError('Directory too large')
        data = json.loads(raw)['data']
        if not isinstance(data, list) or any(not isinstance(row, dict) or not isinstance(row.get('id'), str)
                                             or not row['id'] or len(row['id'].encode()) > 512 for row in data):
            raise ValueError('Invalid directory')
        targets = list(dict.fromkeys(row['id'] for row in data))
        if len(json.dumps(targets).encode()) > 65536:
            raise ValueError('Directory too large')
        value.update({'targets': targets, 'checkedAt': utcnow(),
                      'stale': False, 'error': None})
    except HTTPError as error:
        value.update({'stale': True, 'error': 'authentication' if error.code in (401, 403) else 'network'})
    except (URLError, OSError, TimeoutError):
        value.update({'stale': True, 'error': 'network'})
    except (ValueError, KeyError, TypeError, UnicodeError):
        value.update({'stale': True, 'error': 'invalid_output'})
    with transaction(db):
        current = _record(db, 'service', value['id'])
        if current['endpoint'] != value['endpoint'] or current['type'] != value['type']:
            raise ConfigurationError('Service changed during refresh')
        value['name'] = current['name']
        _store(db, 'service', value)
    return value


def prompt(db, method, body, *, copied=None):
    if method == 'GET':
        if 'id' not in body:
            return _list(db, 'prompt', body)
        with transaction(db):
            value = _record(db, 'prompt', body.get('id'))
            row = db.execute('SELECT id,content FROM prompt_versions WHERE role=? AND (kit_id=? OR (kit_id=? AND rowid<=?)) ORDER BY rowid DESC LIMIT 1',
                             (value['role'], value['id'], value.get('legacyKit'), value.get('legacyMax', 0))).fetchone()
            if row is None:
                raise ConfigurationError('Prompt version missing')
            return {**value, 'versionId': row['id'], 'text': row['content']}
    if method == 'DELETE':
        value = _record(db, 'prompt', body.get('id'))
        with transaction(db):
            if any(item['promptId'] == value['id'] for item in _records(db, 'reference')):
                raise ConfigurationError('Prompt is in use')
            _store(db, 'deleted-prompt', {'id': value['id']})
            db.execute('DELETE FROM app_settings WHERE key=?', (f"nonews.prompt.{value['id']}",))
        return {'deleted': True}
    identity = body.get('id')
    prior = _record(db, 'prompt', identity) if identity is not None else None
    name = _required(body.get('name'))
    role = body.get('role')
    if role not in {'curator', 'editor'} or (prior and prior['role'] != role):
        raise ConfigurationError('Invalid role')
    text = _required(body.get('text'), 200_000)
    service_id = body.get('serviceId')
    connection = _record(db, 'service', service_id)
    target = _required(body.get('target'))
    binding = prior or copied
    unchanged = (binding and binding['serviceId'] == service_id and binding['target'] == target
                 and binding.get('serviceEndpoint') == connection['endpoint'] and binding.get('serviceType') == connection['type'])
    if not unchanged and (connection['stale'] or target not in connection['targets']):
        raise ConfigurationError('Refresh directory and select an available target')
    title = body.get('titleLanguage', 'instructions')
    typography = body.get('typography', 'preserve')
    if title not in {'instructions', 'chinese'} or typography not in {'preserve', 'chinese'}:
        raise ConfigurationError('Invalid output preferences')
    value = {'id': identity or uuid.uuid4().hex, 'name': name, 'role': role,
             'serviceId': service_id, 'target': target, 'serviceEndpoint': connection['endpoint'],
             'serviceType': connection['type'], 'titleLanguage': title, 'typography': typography}
    if prior and prior.get('legacyKit'):
        value.update({key: prior[key] for key in ('legacyKit', 'legacyMax', 'legacyOutputStatus')})
    elif (prior or copied or {}).get('legacyOutputStatus') == 'needs_review':
        value['legacyOutputStatus'] = 'needs_review'
    if value.get('legacyOutputStatus') == 'needs_review' and body.get('confirmLegacyOutput') is True:
        value['legacyOutputStatus'] = 'reviewed'
    with transaction(db):
        if identity is not None:
            current_binding = _record(db, 'prompt', identity)
            if current_binding != prior:
                raise ConfigurationError('Prompt changed during save')
        connection = _record(db, 'service', service_id)
        if value['serviceEndpoint'] != connection['endpoint'] or value['serviceType'] != connection['type']:
            raise ConfigurationError('Service changed during save')
        if not unchanged and (connection['stale'] or target not in connection['targets']):
            raise ConfigurationError('Refresh directory and select an available target')
        current = db.execute('SELECT content FROM prompt_versions WHERE role=? AND (kit_id=? OR (kit_id=? AND rowid<=?)) ORDER BY rowid DESC LIMIT 1',
                             (role, value['id'], value.get('legacyKit'), value.get('legacyMax', 0))).fetchone()
        if current is None or current['content'] != text:
            db.execute('INSERT INTO prompt_versions(id,kit_id,role,content,created_at) VALUES (?,?,?,?,?)',
                       (uuid.uuid4().hex, value['id'], role, text, utcnow()))
        _store(db, 'prompt', value)
    return prompt(db, 'GET', {'id': value['id']})


def history(db, body):
    value = _record(db, 'prompt', body.get('id'))
    version = body.get('versionId')
    if version is not None:
        row = db.execute('SELECT id,content,created_at FROM prompt_versions WHERE role=? AND id=? AND (kit_id=? OR (kit_id=? AND rowid<=?))',
                         (value['role'], version, value['id'], value.get('legacyKit'), value.get('legacyMax', 0))).fetchone()
        if row is None:
            raise ConfigurationError('Prompt version not found')
        return {'id': row['id'], 'text': row['content'], 'createdAt': row['created_at']}
    before = body.get('before')
    if before is not None and (type(before) is not int or before < 1):
        raise ConfigurationError('Invalid history cursor')
    rows = db.execute('SELECT rowid AS position,id,created_at FROM prompt_versions WHERE role=? '
                      'AND (kit_id=? OR (kit_id=? AND rowid<=?)) AND rowid < ? ORDER BY rowid DESC LIMIT 101',
                      (value['role'], value['id'], value.get('legacyKit'), value.get('legacyMax', 0), before or 2**63 - 1)).fetchall()
    return {'versions': [{'id': row['id'], 'createdAt': row['created_at']} for row in rows[:100]],
            'next': rows[99]['position'] if len(rows) > 100 else None}


def copy_prompt(db, body):
    with transaction(db):
        current = prompt(db, 'GET', {'id': body.get('id')})
        edits = body.get('configuration', {})
        if not isinstance(edits, dict):
            raise ConfigurationError('Invalid copy')
        return prompt(db, 'PUT', {**current, **edits, 'id': None, 'name': body.get('name')}, copied=current)


def import_legacy(db, body):
    kit = _required(body.get('kit'))
    role = body.get('role')
    if role not in {'curator', 'editor'}:
        raise ConfigurationError('Invalid role')
    name = _required(body.get('name'))
    target = _required(body.get('target'))
    with transaction(db):
        connection = _record(db, 'service', body.get('serviceId'))
        if connection['stale'] or target not in connection['targets']:
            raise ConfigurationError('Refresh directory and select an available target')
        row = db.execute('SELECT rowid AS position,content FROM prompt_versions WHERE kit_id=? AND role=? ORDER BY rowid DESC LIMIT 1', (kit, role)).fetchone()
        if row is None:
            raise ConfigurationError('Legacy prompt not found')
        _required(row['content'], 200_000)
        value = {'id': uuid.uuid4().hex, 'name': name, 'role': role, 'serviceId': connection['id'], 'target': target,
                 'serviceEndpoint': connection['endpoint'], 'serviceType': connection['type'],
                 'titleLanguage': 'chinese', 'typography': 'chinese', 'legacyKit': kit,
                 'legacyMax': row['position'], 'legacyOutputStatus': 'needs_review'}
        _store(db, 'prompt', value)
        return prompt(db, 'GET', {'id': value['id']})


def legacy(db, body):
    after_kit, after_role = body.get('afterKit', ''), body.get('afterRole', '')
    if not isinstance(after_kit, str) or not isinstance(after_role, str) or len(after_kit) > 512 or len(after_role) > 16:
        raise ConfigurationError('Invalid legacy cursor')
    rows = db.execute('''SELECT p.kit_id,p.role,p.id,p.created_at FROM prompt_versions p
        WHERE p.role IN ('curator','editor') AND (p.kit_id>? OR (p.kit_id=? AND p.role>?))
          AND NOT EXISTS (SELECT 1 FROM app_settings s WHERE s.key='nonews.prompt.' || p.kit_id)
          AND NOT EXISTS (SELECT 1 FROM app_settings s WHERE s.key='nonews.deleted-prompt.' || p.kit_id)
          AND p.rowid=(SELECT max(q.rowid) FROM prompt_versions q WHERE q.kit_id=p.kit_id AND q.role=p.role)
        ORDER BY p.kit_id,p.role LIMIT 101''', (after_kit, after_kit, after_role)).fetchall()
    items = [{'kit': row['kit_id'], 'role': row['role'], 'versionId': row['id'], 'createdAt': row['created_at']} for row in rows[:100]]
    return {'prompts': items, 'next': {'afterKit': items[-1]['kit'], 'afterRole': items[-1]['role']} if len(rows) > 100 else None}


def restore(db, body):
    with transaction(db):
        current = prompt(db, 'GET', {'id': body.get('id')})
        old = history(db, {'id': current['id'], 'versionId': body.get('versionId')})
        edits = body.get('configuration', {})
        if not isinstance(edits, dict):
            raise ConfigurationError('Invalid restore')
        return prompt(db, 'PUT', {**current, **edits, 'id': current['id'], 'text': old['text']})


def render(db, body):
    current = prompt(db, 'GET', {'id': body.get('id')})
    version = body.get('versionId')
    template = history(db, {'id': current['id'], 'versionId': version})['text'] if version else current['text']
    values = body.get('values')
    if not isinstance(values, dict) or any(not isinstance(key, str) or not isinstance(value, str) for key, value in values.items()):
        raise ConfigurationError('Invalid materials')
    expanded = dict(values)
    if 'content' in values:
        expanded.setdefault('description', values['content'])
    if 'abstract' in values:
        expanded.setdefault('content', values['abstract'])
        expanded.setdefault('description', values['abstract'])
    pattern = re.compile(r'\{\{([^{}]*)\}\}')
    names = pattern.findall(template)
    unknown = sorted(set(name for name in names if name not in expanded))
    if unknown:
        raise PlaceholderError([name[:256] for name in unknown[:100]])
    if len(template.encode()) + sum(len(expanded[name].encode()) for name in names) > 1_000_000:
        raise ConfigurationError('Material exceeds transport capacity')
    return {'text': pattern.sub(lambda match: expanded[match.group(1)], template)}


def bind(db, body):
    with transaction(db):
        value = prompt(db, 'GET', {'id': body.get('id')})
        if value.get('legacyOutputStatus') == 'needs_review':
            raise ConfigurationError('Review imported output preferences')
        connection = _record(db, 'service', value['serviceId'])
        if value.get('serviceEndpoint') != connection['endpoint'] or value.get('serviceType') != connection['type']:
            raise ConfigurationError('Bound service endpoint changed')
        return value


def _records(db, kind):
    rows = db.execute('SELECT value FROM app_settings WHERE key >= ? AND key < ? ORDER BY key',
                      (f'nonews.{kind}.', f'nonews.{kind}/'))
    return (json.loads(row[0]) for row in rows)


def _list(db, kind, body):
    after = body.get('after', '')
    if not isinstance(after, str) or (after and (len(after) != 32 or any(c not in '0123456789abcdef' for c in after))):
        raise ConfigurationError('Invalid cursor')
    prefix = f'nonews.{kind}.'
    rows = db.execute('SELECT value FROM app_settings WHERE key > ? AND key < ? ORDER BY key LIMIT 101',
                      (prefix + after, f'nonews.{kind}/')).fetchall()
    values = [json.loads(row[0]) for row in rows[:100]]
    if kind == 'service':
        values = [{key: value[key] for key in ('id', 'name', 'type', 'endpoint')} for value in values]
    return {kind + 's': values, 'next': values[-1]['id'] if len(rows) > 100 else None}


def references(db, method, body):
    if method == 'GET':
        value = _record(db, 'prompt', body.get('promptId'))
        return {'references': [row for row in _records(db, 'reference') if row['promptId'] == value['id']]}
    if method == 'DELETE':
        value = _record(db, 'reference', body.get('id'))
        db.execute('DELETE FROM app_settings WHERE key=?', (f"nonews.reference.{value['id']}",))
        return {'deleted': True}
    source = _required(body.get('sourceId'))
    name = _required(body.get('name'))
    value = _record(db, 'prompt', body.get('promptId'))
    if body.get('role') != value['role']:
        raise ConfigurationError('Reference role mismatch')
    identity = uuid.uuid5(uuid.NAMESPACE_URL, source + '\0' + value['role']).hex
    reference = {'id': identity, 'sourceId': source, 'name': name, 'role': value['role'], 'promptId': value['id']}
    with transaction(db):
        _record(db, 'prompt', value['id'])
        _store(db, 'reference', reference)
    return reference
