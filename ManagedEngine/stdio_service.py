"""Private stdio adapter for an explicitly supplied Information OS application."""
import hmac
import json
import os
import sqlite3
from pathlib import Path
import sys

# 200,000 UTF-8 bytes can expand to 1,200,000 bytes when JSON-escaped.
MAX_MESSAGE = 1_310_720
MAX_REFUSAL_PARSE = 8 * 1024 * 1024
ALLOWED = {('GET', '/api/status'), ('GET', '/api/jobs'), ('GET', '/api/settings/processing'),
           ('PUT', '/api/settings/processing'), ('POST', '/api/settings/processing/probe'),
           ('GET', '/api/config/services'), ('PUT', '/api/config/services'),
           ('GET', '/api/config/prompts'), ('PUT', '/api/config/prompts'),
           ('GET', '/api/config/history'), ('POST', '/api/config/copy'), ('POST', '/api/config/restore'),
           ('POST', '/api/config/refresh'), ('DELETE', '/api/config/services'), ('DELETE', '/api/config/prompts'),
           ('GET', '/api/config/references'), ('PUT', '/api/config/references'), ('DELETE', '/api/config/references'),
           ('POST', '/api/config/render'), ('POST', '/api/config/bind'), ('POST', '/api/config/import-legacy'), ('GET', '/api/config/legacy'), ('POST', '/api/config/migration/preview'),
           ('POST', '/api/config/migration/pause'), ('POST', '/api/config/migration/apply'), ('POST', '/api/config/migration/release'),
           ('POST', '/api/config/migration/operation'), ('POST', '/api/config/migration/ack'),
           ('GET', '/api/native/observations'), ('POST', '/api/native/observations'),
           ('GET', '/api/native/observation'), ('POST', '/api/native/jobs/claim'), ('POST', '/api/native/jobs/complete'), ('POST', '/api/native/replay'), ('GET', '/api/native/context/results'), ('POST', '/api/native/context/results'), ('GET', '/api/settings/feeds'), ('PUT', '/api/settings/feeds')}


def read_message():
    line = sys.stdin.buffer.readline(MAX_MESSAGE + 1)
    if not line:
        return None
    oversized = len(line) > MAX_MESSAGE or not line.endswith(b'\n')
    if oversized:
        data = bytearray(line)
        while not line.endswith(b'\n'):
            line = sys.stdin.buffer.readline(65536)
            if not line:
                raise ValueError('incomplete message')
            if data is not None:
                if len(data) + len(line) <= MAX_REFUSAL_PARSE:
                    data.extend(line)
                else:
                    data = None
        if data is None:
            return (None, True)
        line = data
    try:
        message = json.loads(line)
    except (ValueError, UnicodeError, RecursionError):
        if oversized:
            return (None, True)
        raise
    if not isinstance(message, dict):
        if oversized:
            return (None, True)
        raise ValueError('invalid message')
    return message, oversized


def send(message):
    encoded = json.dumps(message, separators=(',', ':'), ensure_ascii=True)
    if len(encoded) + 1 > MAX_MESSAGE:
        replacement = {'error': 'response too large'}
        if 'id' in message:
            replacement['id'] = message['id']
        encoded = json.dumps(replacement, separators=(',', ':'))
    print(encoded, flush=True)


def main():
    if len(sys.argv) != 2:
        return 2
    try:
        bootstrap = read_message()
        token = bootstrap[0].get('token') if bootstrap and bootstrap[0] and not bootstrap[1] else None
        if not isinstance(token, str) or len(token) < 24 or not token.isascii():
            return 2
        for key in tuple(os.environ):
            if key.startswith('INFORMATION_OS_'):
                del os.environ[key]
        try:
            from backend.schema import UnsupportedSchemaError
        except Exception:
            send({'status': 'error', 'code': 'startup_failed'})
            return 1
        try:
            from backend.server import Application
            root = Path(sys.argv[1])
            root.mkdir(parents=True, exist_ok=True)
            app = Application(root / 'information.sqlite', root / 'raw', root / 'artifacts',
                              token=token, write_scope='settings')
            app.handle('GET', '/api/status', {}, {})
            app.handle('GET', '/api/settings/processing', {}, {})
            app.handle('POST', '/api/settings/processing/probe', {}, {})
        except UnsupportedSchemaError as error:
            send({'status': 'error', 'code': error.code})
            return 1
        except sqlite3.DatabaseError as error:
            code = getattr(error, 'sqlite_errorcode', None)
            kind = 'data_corrupt' if code in {sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB} else 'data_unavailable'
            send({'status': 'error', 'code': kind})
            return 1
        except (OSError, PermissionError):
            send({'status': 'error', 'code': 'data_unavailable'})
            return 1
        except Exception:
            send({'status': 'error', 'code': 'startup_failed'})
            return 1
        send({'status': 'ready'})
        try:
            while True:
                frame = read_message()
                if frame is None:
                    return 0
                message, oversized = frame
                if message is None:
                    send({'error': 'invalid message'})
                    continue
                supplied = message.get('token')
                if not isinstance(supplied, str) or not supplied.isascii() or not hmac.compare_digest(token, supplied):
                    send({'error': 'unauthorized'})
                    continue
                request_id = message.get('id')
                if request_id is not None and (type(request_id) is not int or not 0 <= request_id < 2**53):
                    send({'error': 'invalid request id'})
                    continue
                correlation = {} if request_id is None else {'id': request_id}
                if oversized:
                    send({**correlation, 'error': 'invalid configuration', 'code': 'invalid_configuration'})
                    continue
                method, path = message.get('method'), message.get('path')
                mutation_id = message.get('mutationId')
                if mutation_id is not None and (not isinstance(mutation_id, str) or len(mutation_id) != 32 or any(c not in '0123456789abcdef' for c in mutation_id)):
                    send({**correlation, 'error': 'invalid operation'})
                    continue
                body = message.get('body', {})
                query = message.get('query', {})
                if not isinstance(method, str) or not isinstance(path, str) or (method, path) not in ALLOWED or not isinstance(body, dict):
                    send({**correlation, 'error': 'invalid operation'})
                    continue
                if not isinstance(query, dict) or (path != '/api/jobs' and query) or (path == '/api/jobs' and
                        (set(query) - {'cursor'} or ('cursor' in query and (not isinstance(query['cursor'], str) or len(query['cursor']) > 100)))):
                    send({**correlation, 'error': 'invalid query'})
                    continue
                try:
                    if path == '/api/config/render':
                        envelope = json.dumps({**correlation, 'result': {'text': ''}}, separators=(',', ':'), ensure_ascii=True)
                        result = app.handle(method, path, query, body, response_budget=MAX_MESSAGE - len(envelope) - 1, mutation_id=mutation_id)
                    elif path == '/api/config/migration/operation':
                        envelope = json.dumps({**correlation, 'result': {}}, separators=(',', ':'), ensure_ascii=True)
                        result = app.handle(method, path, query, body, response_budget=MAX_MESSAGE - len(envelope) + 1)
                    elif method == 'GET' and path == '/api/config/services':
                        envelope = json.dumps({**correlation, 'result': {}}, separators=(',', ':'), ensure_ascii=True)
                        result = app.handle(method, path, query, body, response_budget=MAX_MESSAGE - len(envelope) - 1)
                    else:
                        if mutation_id is None:
                            result = app.handle(method, path, query, body)
                        else:
                            result = app.handle(method, path, query, body, mutation_id=mutation_id)
                    send({**correlation, 'result': result})
                except ValueError as error:
                    if getattr(error, 'code', None) == 'job_record_too_large':
                        send({**correlation, 'error': 'job record is too large', 'code': 'job_record_too_large'})
                    elif getattr(error, 'code', None) == 'invalid_configuration':
                        details = {'placeholders': error.names} if hasattr(error, 'names') else {}
                        send({**correlation, 'error': 'invalid configuration', 'code': 'invalid_configuration', **details})
                    elif getattr(error, 'code', None) == 'render_too_large':
                        send({**correlation, 'error': 'rendered response is too large', 'code': 'render_too_large'})
                    elif getattr(error, 'code', None) == 'snapshot_expired':
                        send({**correlation, 'error': 'migration report expired', 'code': 'snapshot_expired'})
                    elif getattr(error, 'code', None) == 'migration_busy':
                        send({**correlation, 'error': 'migration is in progress', 'code': 'migration_busy'})
                    elif getattr(error, 'code', None) == 'snapshot_capacity':
                        send({**correlation, 'error': 'migration report exceeds snapshot capacity', 'code': 'snapshot_capacity'})
                    else:
                        send({**correlation, 'error': 'invalid query'})
                except Exception:
                    send({**correlation, 'error': 'operation failed'})
        finally:
            close = getattr(app, 'close', None)
            if callable(close):
                close()
    except Exception:
        return 1


if __name__ == '__main__':
    sys.exit(main())
