"""User-owned configuration; prompt text versions retain IO's history table."""
import json
import uuid
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlsplit, urlunsplit

from .core import transaction, utcnow


class ConfigurationError(ValueError):
    code = 'invalid_configuration'


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
        with build_opener(_NoRedirect).open(request, timeout=15) as response:
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


def prompt(db, method, body):
    if method == 'GET':
        value = _record(db, 'prompt', body.get('id'))
        row = db.execute('SELECT id,content FROM prompt_versions WHERE kit_id=? AND role=? ORDER BY rowid DESC LIMIT 1',
                         (value['id'], value['role'])).fetchone()
        if row is None:
            raise ConfigurationError('Prompt version missing')
        return {**value, 'versionId': row['id'], 'text': row['content']}
    if method == 'DELETE':
        value = _record(db, 'prompt', body.get('id'))
        with transaction(db):
            if any(item['promptId'] == value['id'] for item in _records(db, 'reference')):
                raise ConfigurationError('Prompt is in use')
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
    unchanged = prior and prior['serviceId'] == service_id and prior['target'] == target
    if not unchanged and (connection['stale'] or target not in connection['targets']):
        raise ConfigurationError('Refresh directory and select an available target')
    title = body.get('titleLanguage', 'instructions')
    typography = body.get('typography', 'preserve')
    if title not in {'instructions', 'chinese'} or typography not in {'preserve', 'chinese'}:
        raise ConfigurationError('Invalid output preferences')
    value = {'id': identity or uuid.uuid4().hex, 'name': name, 'role': role,
             'serviceId': service_id, 'target': target, 'titleLanguage': title, 'typography': typography}
    with transaction(db):
        connection = _record(db, 'service', service_id)
        if not unchanged and (connection['stale'] or target not in connection['targets']):
            raise ConfigurationError('Refresh directory and select an available target')
        current = db.execute('SELECT content FROM prompt_versions WHERE kit_id=? AND role=? ORDER BY rowid DESC LIMIT 1',
                             (value['id'], role)).fetchone()
        if current is None or current['content'] != text:
            db.execute('INSERT INTO prompt_versions(id,kit_id,role,content,created_at) VALUES (?,?,?,?,?)',
                       (uuid.uuid4().hex, value['id'], role, text, utcnow()))
        _store(db, 'prompt', value)
    return prompt(db, 'GET', {'id': value['id']})


def history(db, body):
    value = _record(db, 'prompt', body.get('id'))
    version = body.get('versionId')
    if version is not None:
        row = db.execute('SELECT id,content,created_at FROM prompt_versions WHERE kit_id=? AND role=? AND id=?',
                         (value['id'], value['role'], version)).fetchone()
        if row is None:
            raise ConfigurationError('Prompt version not found')
        return {'id': row['id'], 'text': row['content'], 'createdAt': row['created_at']}
    before = body.get('before')
    if before is not None and (type(before) is not int or before < 1):
        raise ConfigurationError('Invalid history cursor')
    rows = db.execute('SELECT rowid AS position,id,created_at FROM prompt_versions WHERE kit_id=? AND role=? '
                      'AND rowid < ? ORDER BY rowid DESC LIMIT 101',
                      (value['id'], value['role'], before or 2**63 - 1)).fetchall()
    return {'versions': [{'id': row['id'], 'createdAt': row['created_at']} for row in rows[:100]],
            'next': rows[99]['position'] if len(rows) > 100 else None}


def copy_prompt(db, body):
    current = prompt(db, 'GET', {'id': body.get('id')})
    return prompt(db, 'PUT', {**current, 'id': None, 'name': body.get('name')})


def restore(db, body):
    current = prompt(db, 'GET', {'id': body.get('id')})
    old = history(db, {'id': current['id'], 'versionId': body.get('versionId')})
    return prompt(db, 'PUT', {**current, 'text': old['text']})


def _records(db, kind):
    rows = db.execute('SELECT value FROM app_settings WHERE key >= ? AND key < ? ORDER BY key',
                      (f'nonews.{kind}.', f'nonews.{kind}/'))
    return (json.loads(row[0]) for row in rows)


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
