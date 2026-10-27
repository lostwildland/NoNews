"""Private stdio adapter for an explicitly supplied Information OS application."""
import hmac
import json
import os
from pathlib import Path
import sys

MAX_MESSAGE = 65536
ALLOWED = {('GET', '/api/jobs'), ('GET', '/api/settings/processing'),
           ('PUT', '/api/settings/processing')}


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
    print(json.dumps(message, separators=(',', ':')), flush=True)


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
        from backend.server import Application
        root = Path(sys.argv[1])
        root.mkdir(parents=True, exist_ok=True)
        app = Application(root / 'information.sqlite', root / 'raw', root / 'artifacts',
                          token=token, write_scope='settings')
        app.handle('GET', '/api/jobs', {}, {})
        app.handle('GET', '/api/settings/processing', {}, {})
        send({'status': 'ready'})
        while True:
            message = read_message()
            if message is None:
                return 0
            supplied = message.get('token')
            if not isinstance(supplied, str) or not supplied.isascii() or not hmac.compare_digest(token, supplied):
                send({'error': 'unauthorized'})
                continue
            method, path = message.get('method'), message.get('path')
            body = message.get('body', {})
            if not isinstance(method, str) or not isinstance(path, str) or (method, path) not in ALLOWED or not isinstance(body, dict):
                send({'error': 'invalid operation'})
                continue
            try:
                send({'result': app.handle(method, path, {}, body)})
            except Exception:
                send({'error': 'operation failed'})
    except Exception:
        return 1


if __name__ == '__main__':
    sys.exit(main())
