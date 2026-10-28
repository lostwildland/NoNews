"""Private stdio adapter for an explicitly supplied Information OS application."""
import hmac
import json
import os
import sqlite3
from pathlib import Path
import sys

# 200,000 UTF-8 bytes can expand to 1,200,000 bytes when JSON-escaped.
MAX_MESSAGE = 1_310_720
ALLOWED = {('GET', '/api/status'), ('GET', '/api/jobs'), ('GET', '/api/settings/processing'),
           ('PUT', '/api/settings/processing'), ('POST', '/api/settings/processing/probe')}


def read_message():
    line = sys.stdin.buffer.readline(MAX_MESSAGE + 1)
    if not line:
        return None
    if len(line) > MAX_MESSAGE or not line.endswith(b'\n'):
        raise ValueError('invalid message')
    message = json.loads(line)
    if not isinstance(message, dict):
        raise ValueError('invalid message')
    return message


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
        token = bootstrap.get('token') if bootstrap else None
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
                message = read_message()
                if message is None:
                    return 0
                supplied = message.get('token')
                if not isinstance(supplied, str) or not supplied.isascii() or not hmac.compare_digest(token, supplied):
                    send({'error': 'unauthorized'})
                    continue
                request_id = message.get('id')
                if request_id is not None and (type(request_id) is not int or not 0 <= request_id < 2**53):
                    send({'error': 'invalid request id'})
                    continue
                correlation = {} if request_id is None else {'id': request_id}
                method, path = message.get('method'), message.get('path')
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
                    send({**correlation, 'result': app.handle(method, path, query, body)})
                except ValueError as error:
                    if getattr(error, 'code', None) == 'job_record_too_large':
                        send({**correlation, 'error': 'job record is too large', 'code': 'job_record_too_large'})
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
