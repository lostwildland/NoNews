import json
import os
import signal
from pathlib import Path
import sys
import time

mode = Path(__file__).stem
if mode == 'stubborn':
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
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
    print('x' * 65537, flush=True)
    time.sleep(10)
    sys.exit()
assert 'INFORMATION_OS_RAW_VAULT' not in os.environ
bootstrap = json.loads(sys.stdin.readline())
token = bootstrap['token']
assert len(token) >= 24
print(json.dumps({'status': 'ready'}), flush=True)
root = Path(sys.argv[1])
setting = root / 'fixture-setting'
for line in sys.stdin:
    request = json.loads(line)
    assert request['token'] == token
    path = request['path']
    if request['method'] == 'PUT' and mode == 'requesttimeout':
        time.sleep(10)
    if request['method'] == 'PUT' and mode == 'requestcrash':
        sys.exit(1)
    if request['method'] == 'PUT' and mode == 'badreply':
        print(json.dumps({'id': request['id']}), flush=True)
        continue
    if path == '/api/jobs':
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
