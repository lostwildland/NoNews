"""Synthetic stdio peer for native recovery and acknowledgement interleavings."""
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
json.loads(sys.stdin.readline())
print(json.dumps({'status': 'ready'}), flush=True)
for line in sys.stdin:
    request = json.loads(line)
    body, path = request.get('body', {}), request['path']
    mode = (root / 'mode').read_text()
    result = {}
    if path == '/api/status':
        result = {'schemaVersion': 41}
    elif path == '/api/settings/processing':
        result = {'processors': 1}
    elif path == '/api/settings/processing/probe':
        result = {'writable': True}
    elif path == '/api/config/services' and request['method'] == 'PUT':
        result = {'_pendingMutation': request['mutationId']}
    elif path == '/api/config/migration/operation':
        identity = body['operationId']
        if mode.startswith('complete'):
            result = {'operationId': identity, 'state': 'complete', 'result': {'id': 'saved'}}
        elif mode == 'rejected':
            result = {'operationId': identity, 'state': 'rejected', 'code': 'invalid_configuration'}
        elif mode == 'poll-fail':
            print(json.dumps({'id': request['id'], 'error': 'Synthetic polling failure', 'code': 'invalid_configuration'}), flush=True)
            continue
        else:
            result = {'operationId': identity, 'state': 'unknown'}
    elif path == '/api/config/migration/ack':
        identity = body.get('operationId', 'ack-operation')
        if 'operationId' not in body or mode == 'ack-pending':
            result = {'operationId': identity, 'state': 'running'}
        elif mode in ('ack-fail', 'complete-ack-fail'):
            print(json.dumps({'id': request['id'], 'error': 'Synthetic acknowledgement failure', 'code': 'invalid_configuration'}), flush=True)
            continue
        else:
            result = {'operationId': 'wrong-operation' if mode == 'ack-wrong' else identity,
                      'state': 'complete', 'result': {'acknowledged': True}}
    elif path == '/api/config/services':
        result = {'services': []}
    elif path == '/api/config/prompts':
        result = {'prompts': []}
    print(json.dumps({'id': request['id'], 'result': result}), flush=True)
