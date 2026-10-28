import json
import sqlite3
import os
import signal
from pathlib import Path
import sys
import time

mode = Path(__file__).stem
if mode in {'stubborn', 'failstubborn'}:
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
if mode.startswith('startup_'):
    print(json.dumps({'status': 'error', 'code': mode.removeprefix('startup_')}), flush=True)
    sys.exit(1)
if mode == 'closedstdout':
    os.close(1)
    time.sleep(10)
    sys.exit()
if mode == 'timeout':
    time.sleep(10)
    sys.exit()
if mode == 'crash':
    sys.exit(1)
if mode == 'malformed':
    print('{bad', flush=True)
    time.sleep(10)
    sys.exit()
if mode == 'oversize':
    print('x' * 1310721, flush=True)
    time.sleep(10)
    sys.exit()
assert 'INFORMATION_OS_RAW_VAULT' not in os.environ
bootstrap = json.loads(sys.stdin.readline())
token = bootstrap['token']
assert len(token) >= 24
print(json.dumps({'status': 'ready'}), flush=True)
root = Path(sys.argv[1])
if mode == 'failstubborn':
    with (root / 'owners').open('a') as owners:
        owners.write(str(os.getpid()) + '\n')
    ownership = sqlite3.connect(root / 'owner.sqlite', timeout=0)
    ownership.execute('BEGIN EXCLUSIVE')
setting = root / 'fixture-setting'
for line in sys.stdin:
    request = json.loads(line)
    assert request['token'] == token
    path = request['path']
    if request['method'] == 'PUT' and mode in {'requesttimeout', 'failstubborn'}:
        time.sleep(10)
    if request['method'] == 'PUT' and mode == 'requestcrash':
        sys.exit(1)
    if request['method'] == 'PUT' and mode == 'badreply':
        print(json.dumps({'id': request['id']}), flush=True)
        continue
    if path == '/api/settings/processing/probe':
        result = {'writable': True}
    elif path == '/api/status':
        result = {'schemaVersion': 42}
    elif path == '/api/jobs':
        cursor = request.get('query', {}).get('cursor')
        if cursor in {'capacity', 'invalid', 'unknown'}:
            reply = {'id': request['id'], 'error': 'invalid query'}
            if cursor == 'capacity':
                reply.update(error='job record is too large', code='job_record_too_large')
            elif cursor == 'unknown':
                reply['code'] = 'untrusted_synthetic_code'
            print(json.dumps(reply), flush=True)
            continue
        result = {'jobs': []}
    elif request['method'] == 'PUT':
        value = request['body']['processors']
        setting.write_text(str(value))
        result = {'processors': value}
    else:
        result = {'processors': int(setting.read_text()) if setting.exists() else 1}
    print(json.dumps({'id': request['id'], 'result': result}), flush=True)

if mode == 'stubborn':
    time.sleep(20)
