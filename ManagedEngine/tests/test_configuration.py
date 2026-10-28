"""Public stdio configuration journeys against the real managed service."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread


class ConfigurationTest(unittest.TestCase):
    def setUp(self):
        class Directory(BaseHTTPRequestHandler):
            def do_GET(self):
                data = b'{"data":[{"id":"route/Exact"},{"id":"a"},{"id":"b"}]}'
                self.send_response(200)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            def log_message(self, *_):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Directory)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.endpoint = f'http://127.0.0.1:{server.server_port}'
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)

    def test_explicit_directory_refresh_preserves_exact_targets_and_stales_on_endpoint_change(self):
        observed = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append(self.path)
                data = b'{"data":[{"id":"Route/Exact"},{"id":"route/exact"}]}'
                self.send_response(200)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            def log_message(self, *_):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        script = Path(__file__).resolve().parents[1] / 'stdio_service.py'
        token = 'c' * 32
        with tempfile.TemporaryDirectory() as root:
            process = subprocess.Popen([sys.executable, str(script), root], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       text=True, env={'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'})
            self.addCleanup(process.wait)
            self.addCleanup(process.stdout.close)
            self.addCleanup(process.stdin.close)
            def call(method, path, body):
                process.stdin.write(json.dumps({'id': 1, 'token': token, 'method': method, 'path': path, 'body': body}) + '\n')
                process.stdin.flush()
                return json.loads(process.stdout.readline())['result']
            process.stdin.write(json.dumps({'token': token}) + '\n')
            process.stdin.flush()
            self.assertEqual(json.loads(process.stdout.readline()), {'status': 'ready'})
            service = call('PUT', '/api/config/services', {'name': 'Gateway', 'type': 'magpie',
                'endpoint': f'http://127.0.0.1:{server.server_port}/v1'})
            self.assertEqual(observed, [])
            refreshed = call('POST', '/api/config/refresh', {'id': service['id']})
            self.assertEqual(refreshed['targets'], ['Route/Exact', 'route/exact'])
            self.assertEqual(observed, ['/v1/models'])
            process.stdin.write(json.dumps({'id': 2, 'token': token, 'method': 'PUT', 'path': '/api/config/prompts',
                'body': {'name': 'Invalid', 'role': 'curator', 'text': 'Text', 'serviceId': service['id'], 'target': 'missing'}}) + '\n')
            process.stdin.flush()
            self.assertEqual(json.loads(process.stdout.readline())['code'], 'invalid_configuration')
            accepted = call('PUT', '/api/config/prompts', {'name': 'Valid', 'role': 'curator', 'text': 'Text',
                'serviceId': service['id'], 'target': 'Route/Exact'})
            self.assertEqual(accepted['target'], 'Route/Exact')
            changed = call('PUT', '/api/config/services', {**service, 'endpoint': 'https://example.invalid'})
            self.assertTrue(changed['stale'])
            self.assertEqual(changed['targets'], [])

    def test_prompt_history_copy_and_restore_keep_visible_binding(self):
        script = Path(__file__).resolve().parents[1] / 'stdio_service.py'
        token = 'b' * 32
        with tempfile.TemporaryDirectory() as root:
            process = subprocess.Popen([sys.executable, str(script), root], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, text=True, env={'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'})
            self.addCleanup(process.wait)
            self.addCleanup(process.stdout.close)
            self.addCleanup(process.stdin.close)
            def exchange(message):
                process.stdin.write(json.dumps(message) + '\n')
                process.stdin.flush()
                return json.loads(process.stdout.readline())
            self.assertEqual(exchange({'token': token}), {'status': 'ready'})
            def call(method, path, body):
                return exchange({'id': 1, 'token': token, 'method': method, 'path': path, 'body': body})['result']
            service = call('PUT', '/api/config/services', {'name': 'Gateway', 'type': 'magpie', 'endpoint': self.endpoint})
            call('POST', '/api/config/refresh', {'id': service['id']})
            first = call('PUT', '/api/config/prompts', {'name': 'First', 'role': 'editor', 'text': 'Original', 'serviceId': service['id'], 'target': 'a'})
            renamed = call('PUT', '/api/config/prompts', {**first, 'name': 'Renamed', 'target': 'b'})
            self.assertEqual(renamed['versionId'], first['versionId'])
            changed = call('PUT', '/api/config/prompts', {**renamed, 'text': 'Revised'})
            changed = call('PUT', '/api/config/prompts', {**changed, 'titleLanguage': 'chinese', 'typography': 'chinese'})
            history = call('GET', '/api/config/history', {'id': first['id']})
            self.assertEqual([x['id'] for x in history['versions']], [changed['versionId'], first['versionId']])
            self.assertEqual(call('GET', '/api/config/history', {'id': first['id'], 'versionId': first['versionId']})['text'], 'Original')
            copy = call('POST', '/api/config/copy', {'id': first['id'], 'name': 'Independent'})
            self.assertNotEqual(copy['id'], first['id'])
            self.assertEqual((copy['text'], copy['target'], copy['titleLanguage'], copy['typography']), ('Revised', 'b', 'chinese', 'chinese'))
            restored = call('POST', '/api/config/restore', {'id': first['id'], 'versionId': first['versionId']})
            self.assertEqual((restored['text'], restored['target'], restored['titleLanguage'], restored['typography']), ('Original', 'b', 'chinese', 'chinese'))
            self.assertNotEqual(restored['versionId'], first['versionId'])
            self.assertEqual(call('POST', '/api/config/restore', {'id': first['id'], 'versionId': first['versionId']})['versionId'], restored['versionId'])
            reference = call('PUT', '/api/config/references', {'sourceId': 'synthetic-source', 'name': 'Source A',
                                                               'role': 'editor', 'promptId': first['id']})
            self.assertEqual(call('GET', '/api/config/references', {'promptId': first['id']})['references'], [reference])
            process.stdin.write(json.dumps({'id': 2, 'token': token, 'method': 'DELETE', 'path': '/api/config/prompts',
                                            'body': {'id': first['id']}}) + '\n')
            process.stdin.flush()
            self.assertEqual(json.loads(process.stdout.readline())['code'], 'invalid_configuration')
            call('DELETE', '/api/config/references', {'id': reference['id']})
            call('DELETE', '/api/config/prompts', {'id': first['id']})
            self.assertEqual(call('GET', '/api/config/prompts', {'id': copy['id']})['text'], 'Revised')

    def test_service_and_prompt_survive_restart_at_utf8_limit(self):
        script = Path(__file__).resolve().parents[1] / 'stdio_service.py'
        token = 'a' * 32
        with tempfile.TemporaryDirectory() as root:
            def session(requests):
                process = subprocess.run([sys.executable, str(script), root],
                    input=''.join(json.dumps(x) + '\n' for x in [{'token': token}, *requests]),
                    text=True, capture_output=True, timeout=30,
                    env={'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'})
                self.assertEqual(process.returncode, 0, process.stderr)
                return [json.loads(line) for line in process.stdout.splitlines()][1:]

            def request(number, method, path, body):
                return {'id': number, 'token': token, 'method': method, 'path': path, 'body': body}

            service = session([request(1, 'PUT', '/api/config/services',
                                       {'name': 'Local gateway', 'type': 'magpie', 'endpoint': self.endpoint + '/v1'})])[0]['result']
            session([request(7, 'POST', '/api/config/refresh', {'id': service['id']})])
            text = '\u0001' * 199996 + '😀'
            saved = session([request(2, 'PUT', '/api/config/prompts',
                {'name': 'Careful reader', 'role': 'curator', 'text': text,
                 'serviceId': service['id'], 'target': 'route/Exact'})])[0]['result']
            reply = session([request(3, 'GET', '/api/config/prompts', {'id': saved['id']})])[0]['result']
            self.assertEqual((reply['id'], reply['name'], reply['role'], reply['text'], reply['serviceId'], reply['target']),
                             (saved['id'], 'Careful reader', 'curator', text, service['id'], 'route/Exact'))
            self.assertEqual(reply['versionId'], saved['versionId'])
            rejected, readback, status = session([
                request(4, 'PUT', '/api/config/prompts', {**reply, 'text': text + 'x'}),
                request(5, 'GET', '/api/config/prompts', {'id': saved['id']}),
                request(6, 'GET', '/api/status', {})])
            self.assertEqual(rejected['code'], 'invalid_configuration')
            self.assertEqual(readback['result'], reply)
            self.assertEqual(status['result']['schemaVersion'], 41)
