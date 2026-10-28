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


class RenderCapacityError(ValueError):
    code = 'render_too_large'


def _credential_state(value):
    if value.get('type') == 'magpie':
        return 'not_required'
    return value.get('credentialState') or 'incomplete'


def _connection_state(value):
    checked = value.get('checkedAt')
    suffix = f"; last checked {checked}" if checked else ''
    if value.get('credentialState') == 'incomplete':
        return 'Credential incomplete' + suffix
    if value.get('error') == 'authentication':
        return 'Authentication failed; directory stale' + suffix
    if value.get('error') == 'network':
        return 'Network error; directory stale' + suffix
    if value.get('error') == 'invalid_output':
        return 'Invalid directory response; directory stale' + suffix
    if value.get('stale'):
        return 'Directory stale' + suffix
    return ('Directory checked' + suffix) if checked else 'Directory not checked'


def _record(db, kind, identity):
    if not isinstance(identity, str) or len(identity) != 32 or any(c not in '0123456789abcdef' for c in identity):
        raise ConfigurationError('Invalid identity')
    row = db.execute('SELECT value FROM app_settings WHERE key=?', (f'nonews.{kind}.{identity}',)).fetchone()
    if row is None:
        raise ConfigurationError('Configuration not found')
    value = json.loads(row[0])
    if kind == 'service':
        value['credentialState'] = _credential_state(value)
    if kind == 'service' and value.get('checkedAt'):
        try:
            value['stale'] = bool(value.get('error')) or (datetime.now(timezone.utc) - datetime.fromisoformat(value['checkedAt'])).total_seconds() > 300
        except (TypeError, ValueError):
            value['stale'] = True
    if kind == 'service':
        value['connectionState'] = _connection_state(value)
    return value


def _store(db, kind, value):
    db.execute('INSERT INTO app_settings(key,value,updated_at) VALUES (?,?,?) '
               'ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at',
               (f"nonews.{kind}.{value['id']}", json.dumps(value, ensure_ascii=False), utcnow()))


def _required(value, maximum=512):
    if not isinstance(value, str) or not value.strip() or len(value.encode('utf-8')) > maximum:
        raise ConfigurationError('Invalid configuration value')
    return value


def _legacy_count(value):
    if value.get('legacyKit') and 'legacyCount' not in value:
        raise ConfigurationError('Legacy history requires verified recovery')
    return value.get('legacyCount', 0)


def _legacy_key(identity, position):
    return f'nonews.legacy.{identity}.{position:020d}'


def _current_text(db, value):
    count = _legacy_count(value)
    row = db.execute('SELECT id,content FROM prompt_versions WHERE kit_id=? AND role=? ORDER BY rowid DESC LIMIT 1',
                     (value['id'], value['role'])).fetchone()
    if row is None and count:
        member = db.execute('SELECT value FROM app_settings WHERE key=?', (_legacy_key(value['id'], count),)).fetchone()
        if member:
            row = db.execute('SELECT id,content FROM prompt_versions WHERE id=? AND kit_id=? AND role=?',
                             (member[0], value['legacyKit'], value['role'])).fetchone()
    if row is None:
        raise ConfigurationError('Prompt version missing')
    return row


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
            for item in _records(db, 'migration-binding'):
                if item['serviceId'] == value['id'] and db.execute(
                        'SELECT 1 FROM model_configs WHERE kit_id=? AND role=?', (item['kit'], item['role'])).fetchone():
                    raise ConfigurationError('Service is in use by legacy routing')
            for item in _records(db, 'migration-job'):
                if item['serviceId'] == value['id'] and db.execute(
                        "SELECT 1 FROM processing_jobs WHERE id=? AND status IN ('pending','running')", (item['jobId'],)).fetchone():
                    raise ConfigurationError('Service is in use by pending work')
            db.execute('DELETE FROM app_settings WHERE key=?', (f"nonews.service.{value['id']}",))
        return {'deleted': True}
    with transaction(db):
        if set(body) <= {'id', 'credentialState', 'expectedRevision'} and 'id' in body:
            prior = _record(db, 'service', body.get('id'))
            if not prior.get('revision') or body.get('expectedRevision') != prior['revision'] or prior['type'] != 'openai-compatible':
                raise ConfigurationError('Service changed during credential update')
            state = body.get('credentialState')
            if state not in {'unverified', 'incomplete', 'verified'}:
                raise ConfigurationError('Invalid credential state')
            value = dict(prior)
            value['credentialState'] = state
            value['revision'] = uuid.uuid4().hex
            value['connectionState'] = _connection_state(value)
            _store(db, 'service', value)
            return value
        if set(body) - {'id', 'name', 'type', 'endpoint', 'targets', 'checkedAt', 'stale', 'error', 'credentialState', 'connectionState', 'revision'}:
            raise ConfigurationError('Invalid service fields')
        identity = body.get('id')
        prior = _record(db, 'service', identity) if identity is not None else None
        if prior and 'revision' in body and body['revision'] != prior.get('revision'):
            raise ConfigurationError('Service changed during save')
        if 'credentialState' in body and (not prior or not prior.get('revision')
                or body.get('revision') != prior['revision'] or body['credentialState'] != prior['credentialState']):
            raise ConfigurationError('Credential changes require a scoped update')
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
        value = {'id': identity or uuid.uuid4().hex, 'revision': uuid.uuid4().hex, 'name': name, 'type': kind,
                 'endpoint': urlunsplit((parsed.scheme, parsed.netloc, path, '', ''))}
        if prior and prior['endpoint'] == value['endpoint'] and prior['type'] == kind:
            value.update({key: prior.get(key) for key in ('targets', 'checkedAt', 'stale', 'error')})
        else:
            value.update({'targets': [], 'checkedAt': None, 'stale': True, 'error': None})
        credential_state = body.get('credentialState', prior.get('credentialState') if prior else None)
        if kind == 'magpie':
            value['credentialState'] = 'not_required'
        else:
            value['credentialState'] = credential_state if credential_state in {'unverified', 'incomplete', 'verified'} else 'unverified'
        value['connectionState'] = _connection_state(value)
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
                      'stale': False, 'error': None,
                      'credentialState': 'verified' if value['type'] == 'openai-compatible' else 'not_required'})
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
        value['connectionState'] = _connection_state(value)
        _store(db, 'service', value)
    return value


def prompt(db, method, body, *, copied=None):
    if method == 'GET':
        if 'id' not in body:
            return _list(db, 'prompt', body)
        with transaction(db):
            value = _record(db, 'prompt', body.get('id'))
            row = _current_text(db, value)
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
        _legacy_count(prior)
        value.update({key: prior[key] for key in ('legacyKit', 'legacyCount', 'legacyOutputStatus')})
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
        current = _current_text(db, value) if prior else None
        if current is None or current['content'] != text:
            db.execute('INSERT INTO prompt_versions(id,kit_id,role,content,created_at) VALUES (?,?,?,?,?)',
                       (uuid.uuid4().hex, value['id'], role, text, utcnow()))
        _store(db, 'prompt', value)
    return prompt(db, 'GET', {'id': value['id']})


def history(db, body):
    value = _record(db, 'prompt', body.get('id'))
    count = _legacy_count(value)
    version = body.get('versionId')
    if version is not None:
        member = db.execute('SELECT 1 FROM app_settings WHERE key>=? AND key<? AND value=? LIMIT 1',
                            (_legacy_key(value['id'], 0), _legacy_key(value['id'], count + 1), version)).fetchone() if count else None
        row = db.execute('SELECT id,content,created_at FROM prompt_versions WHERE role=? AND id=? AND kit_id=?',
                         (value['role'], version, value['legacyKit'] if member else value['id'])).fetchone()
        if row is None:
            raise ConfigurationError('Prompt version not found')
        return {'id': row['id'], 'text': row['content'], 'createdAt': row['created_at']}
    before = body.get('before')
    if before is not None and (not isinstance(before, str) or not re.fullmatch(r'(?:o:[0-9a-f]{32}|l:[0-9]{1,20})', before)):
        raise ConfigurationError('Invalid history cursor')
    rows = []
    if before is None or before.startswith('o:'):
        position = 2**63 - 1
        if before:
            cursor = db.execute('SELECT rowid FROM prompt_versions WHERE id=? AND kit_id=? AND role=?',
                                (before[2:], value['id'], value['role'])).fetchone()
            if cursor is None:
                raise ConfigurationError('Invalid history cursor')
            position = cursor[0]
        rows = db.execute('SELECT id,created_at FROM prompt_versions WHERE kit_id=? AND role=? AND rowid<? ORDER BY rowid DESC LIMIT 101',
                          (value['id'], value['role'], position)).fetchall()
        if len(rows) > 100:
            return {'versions': [{'id': row['id'], 'createdAt': row['created_at']} for row in rows[:100]], 'next': 'o:' + rows[99]['id']}
    versions = [{'id': row['id'], 'createdAt': row['created_at']} for row in rows]
    start = int(before[2:]) if before and before.startswith('l:') else count
    if start > count:
        raise ConfigurationError('Invalid history cursor')
    while start > 0 and len(versions) < 100:
        member = db.execute('SELECT value FROM app_settings WHERE key=?', (_legacy_key(value['id'], start),)).fetchone()
        row = db.execute('SELECT id,created_at FROM prompt_versions WHERE id=? AND kit_id=? AND role=?',
                         (member[0], value['legacyKit'], value['role'])).fetchone() if member else None
        if row is None:
            raise ConfigurationError('Legacy prompt version missing')
        versions.append({'id': row['id'], 'createdAt': row['created_at']})
        start -= 1
    return {'versions': versions, 'next': 'l:' + str(start) if start else None}


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
        rows = db.execute('SELECT id,content FROM prompt_versions WHERE kit_id=? AND role=? ORDER BY rowid', (kit, role))
        identity = uuid.uuid4().hex
        count = 0
        content = None
        for row in rows:
            count += 1
            content = row['content']
            db.execute('INSERT INTO app_settings(key,value,updated_at) VALUES (?,?,?)',
                       (_legacy_key(identity, count), row['id'], utcnow()))
        if count == 0:
            raise ConfigurationError('Legacy prompt not found')
        _required(content, 200_000)
        value = {'id': identity, 'name': name, 'role': role, 'serviceId': connection['id'], 'target': target,
                 'serviceEndpoint': connection['endpoint'], 'serviceType': connection['type'],
                 'titleLanguage': 'chinese', 'typography': 'chinese', 'legacyKit': kit,
                 'legacyCount': count, 'legacyOutputStatus': 'needs_review'}
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


def render(db, body, *, wire_budget=1_310_680):
    current = prompt(db, 'GET', {'id': body.get('id')})
    version = body.get('versionId')
    template = history(db, {'id': current['id'], 'versionId': version})['text'] if version else current['text']
    values = body.get('values')
    if not isinstance(values, dict) or any(not isinstance(key, str) or not isinstance(value, str) for key, value in values.items()):
        raise ConfigurationError('Invalid materials')
    media = body.get('media')
    if media not in {'news', 'paper', 'newsletter', 'podcast', 'video'}:
        raise ConfigurationError('Invalid media')
    paper_curator = media == 'paper' and current['role'] == 'curator'
    allowed = {'title', 'content', 'description'} | ({'abstract', 'tag_schema'} if paper_curator else set())
    inputs = {'title', 'abstract' if paper_curator else 'content'}
    expanded = {key: value for key, value in values.items() if key in inputs}
    if 'content' in expanded:
        expanded.setdefault('description', expanded['content'])
    if 'abstract' in expanded:
        expanded.setdefault('content', expanded['abstract'])
        expanded.setdefault('description', expanded['abstract'])
    pattern = re.compile(r'\{\{([^{}]*)\}\}')
    names = pattern.findall(template)
    unknown = sorted(set(name for name in names if name not in allowed or name not in expanded))
    if unknown:
        raise PlaceholderError([name[:256] for name in unknown[:100]])
    parts = []
    position = 0
    size = 0
    encoded_sizes = {}
    for match in pattern.finditer(template):
        literal = template[position:match.start()]
        name = match.group(1)
        if name not in encoded_sizes:
            encoded_sizes[name] = len(json.dumps(expanded[name], ensure_ascii=True)) - 2
        size += len(json.dumps(literal, ensure_ascii=True)) - 2 + encoded_sizes[name]
        if size > wire_budget:
            raise RenderCapacityError('Rendered response exceeds transport capacity')
        parts.extend((literal, expanded[name]))
        position = match.end()
    tail = template[position:]
    size += len(json.dumps(tail, ensure_ascii=True)) - 2
    if size > wire_budget:
        raise RenderCapacityError('Rendered response exceeds transport capacity')
    parts.append(tail)
    return {'text': ''.join(parts)}


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
        values = [_record(db, 'service', value['id']) for value in values]
    return {kind + 's': values, 'next': values[-1]['id'] if len(rows) > 100 else None}


def references(db, method, body):
    if method == 'GET':
        value = _record(db, 'prompt', body.get('promptId'))
        after = body.get('after', '')
        if not isinstance(after, str) or (after and (len(after) != 32 or any(c not in '0123456789abcdef' for c in after))):
            raise ConfigurationError('Invalid reference cursor')
        rows = db.execute("SELECT value FROM app_settings WHERE key>? AND key<? AND json_extract(value,'$.promptId')=? ORDER BY key LIMIT 101",
                          ('nonews.reference.' + after, 'nonews.reference/', value['id'])).fetchall()
        items = [json.loads(row[0]) for row in rows[:100]]
        return {'references': items, 'next': items[-1]['id'] if len(rows) > 100 else None}
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
