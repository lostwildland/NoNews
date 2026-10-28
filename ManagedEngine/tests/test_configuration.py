"""Public stdio configuration journeys against the real managed service."""
import json
import sqlite3
from contextlib import closing
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
        responses = {'status': 200}
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append((self.path, self.headers.get('Authorization')))
                data = b'{"data":[{"id":"Route/Exact"},{"id":"route/exact"}]}'
                self.send_response(responses['status'])
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
            self.assertEqual(observed, [('/v1/models', None)])
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
            process.stdin.write(json.dumps({'id': 3, 'token': token, 'method': 'PUT', 'path': '/api/config/prompts',
                                            'body': {**accepted, 'name': 'Changed'}}) + '\n')
            process.stdin.flush()
            self.assertEqual(json.loads(process.stdout.readline())['code'], 'invalid_configuration')
            direct = call('PUT', '/api/config/services', {'name': 'Direct', 'type': 'openai-compatible',
                          'endpoint': f'http://127.0.0.1:{server.server_port}'})
            process.stdin.write(json.dumps({'id': 4, 'token': token, 'method': 'PUT', 'path': '/api/config/services',
                'body': {'name': 'Unsafe', 'type': 'openai-compatible', 'endpoint': 'http://example.invalid'}}) + '\n')
            process.stdin.flush()
            self.assertEqual(json.loads(process.stdout.readline())['code'], 'invalid_configuration')
            result = call('POST', '/api/config/refresh', {'id': direct['id'], 'credential': 'synthetic-token'})
            self.assertEqual(observed[-1], ('/v1/models', 'Bearer synthetic-token'))
            self.assertNotIn('synthetic-token', json.dumps(result))
            responses['status'] = 401
            failed = call('POST', '/api/config/refresh', {'id': direct['id'], 'credential': 'synthetic-token'})
            self.assertEqual((failed['error'], failed['stale'], failed['targets']),
                             ('authentication', True, ['Route/Exact', 'route/exact']))
            self.assertEqual(failed['checkedAt'], result['checkedAt'])
            self.assertNotIn('synthetic-token', json.dumps(call('GET', '/api/config/services', {'id': direct['id']})))

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
            with closing(sqlite3.connect(Path(root) / 'information.sqlite')) as db, db:
                db.execute("INSERT INTO prompt_versions VALUES ('hole','unused','derived','Unused','2019')")
                db.execute("INSERT INTO prompt_versions VALUES ('legacy-old','legacy-kit','editor','Legacy old','2020-01-01')")
                db.execute("INSERT INTO prompt_versions VALUES ('legacy-current','legacy-kit','editor','Legacy current','2021-01-01')")
            self.assertEqual(call('GET', '/api/config/legacy', {})['prompts'],
                             [{'kit': 'legacy-kit', 'role': 'editor', 'versionId': 'legacy-current', 'createdAt': '2021-01-01'}])
            imported = call('POST', '/api/config/import-legacy', {'kit': 'legacy-kit', 'role': 'editor', 'name': 'Imported',
                            'serviceId': service['id'], 'target': 'a'})
            self.assertEqual((imported['text'], imported['versionId'], imported['titleLanguage'], imported['typography']),
                             ('Legacy current', 'legacy-current', 'chinese', 'chinese'))
            legacy_history = call('GET', '/api/config/history', {'id': imported['id']})['versions']
            self.assertEqual([(row['id'], row['createdAt']) for row in legacy_history],
                             [('legacy-current', '2021-01-01'), ('legacy-old', '2020-01-01')])
            with closing(sqlite3.connect(Path(root) / 'information.sqlite')) as db:
                db.execute("DELETE FROM prompt_versions WHERE id='hole'")
                db.commit()
                db.execute('VACUUM')
                db.execute("UPDATE prompt_versions SET rowid=rowid+1000 WHERE id='legacy-current'")
                db.execute("INSERT INTO prompt_versions VALUES ('later','legacy-kit','editor','Later source edit','2022')")
                db.commit()
            after_vacuum = call('GET', '/api/config/prompts', {'id': imported['id']})
            self.assertEqual((after_vacuum['versionId'], after_vacuum['text']), ('legacy-current', 'Legacy current'))
            self.assertEqual([x['id'] for x in call('GET', '/api/config/history', {'id': imported['id']})['versions']],
                             ['legacy-current', 'legacy-old'])
            process.stdin.write(json.dumps({'id': 3, 'token': token, 'method': 'POST', 'path': '/api/config/bind',
                                            'body': {'id': imported['id']}}) + '\n')
            process.stdin.flush()
            self.assertEqual(json.loads(process.stdout.readline())['code'], 'invalid_configuration')
            imported_edit = call('PUT', '/api/config/prompts', {**imported, 'text': 'Edited independently', 'confirmLegacyOutput': True})
            self.assertEqual(call('POST', '/api/config/bind', {'id': imported['id']})['versionId'], imported_edit['versionId'])
            legacy = call('GET', '/api/config/history', {'id': imported['id'], 'versionId': 'legacy-old'})
            self.assertEqual(legacy['text'], 'Legacy old')
            self.assertNotEqual(imported_edit['versionId'], 'legacy-current')
            first = call('PUT', '/api/config/prompts', {'name': 'First', 'role': 'editor', 'text': 'Original', 'serviceId': service['id'], 'target': 'a'})
            bound = call('POST', '/api/config/bind', {'id': first['id']})
            self.assertEqual((bound['versionId'], bound['target'], bound['titleLanguage']), (first['versionId'], 'a', 'instructions'))
            self.assertEqual([x['id'] for x in call('GET', '/api/config/services', {})['services']], [service['id']])
            self.assertEqual({x['id'] for x in call('GET', '/api/config/prompts', {})['prompts']}, {first['id'], imported['id']})
            with closing(sqlite3.connect(Path(root) / 'information.sqlite')) as db, db:
                db.execute("CREATE TRIGGER reject_prompt_update BEFORE UPDATE ON app_settings WHEN OLD.key LIKE 'nonews.prompt.%' BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END")
            process.stdin.write(json.dumps({'id': 2, 'token': token, 'method': 'PUT', 'path': '/api/config/prompts',
                'body': {**first, 'name': 'Failed', 'text': 'Must roll back', 'target': 'b'}}) + '\n')
            process.stdin.flush()
            self.assertEqual(json.loads(process.stdout.readline())['error'], 'operation failed')
            with closing(sqlite3.connect(Path(root) / 'information.sqlite')) as db, db:
                db.execute('DROP TRIGGER reject_prompt_update')
            self.assertEqual(call('GET', '/api/config/prompts', {'id': first['id']}), first)
            self.assertEqual(len(call('GET', '/api/config/history', {'id': first['id']})['versions']), 1)
            template = call('PUT', '/api/config/prompts', {**first, 'id': None, 'name': 'Template', 'text': '{{title}} {{description}}'})
            rendered = call('POST', '/api/config/render', {'id': template['id'], 'versionId': template['versionId'], 'media': 'news',
                                                              'values': {'title': 'Title', 'content': '{{title}}'}})
            self.assertEqual(rendered['text'], 'Title {{title}}')
            expanded_template = call('PUT', '/api/config/prompts', {**template, 'text': '{{content}}' * 6})
            content = 'a' * 180_000
            expanded = call('POST', '/api/config/render', {'id': template['id'], 'media': 'news', 'values': {'content': content}})
            self.assertEqual(expanded['text'], content * 6)
            escaped = '😀"' * 10_000
            self.assertEqual(call('POST', '/api/config/render', {'id': template['id'], 'media': 'news',
                'values': {'content': escaped}})['text'], escaped * 6)
            process.stdin.write(json.dumps({'id': 99, 'token': token, 'method': 'POST', 'path': '/api/config/render',
                'body': {'id': template['id'], 'media': 'news', 'values': {'content': '\u0001' * 100_000}}}) + '\n')
            process.stdin.flush()
            overflow = json.loads(process.stdout.readline())
            self.assertEqual((overflow['id'], overflow['code']), (99, 'render_too_large'))
            self.assertEqual(call('GET', '/api/status', {})['schemaVersion'], 41)
            call('PUT', '/api/config/prompts', {**template, 'text': '{{missing}}'})
            process.stdin.write(json.dumps({'id': 2, 'token': token, 'method': 'POST', 'path': '/api/config/render',
                'body': {'id': template['id'], 'media': 'news', 'values': {'title': 'Title', 'missing': 'invented'}}}) + '\n')
            process.stdin.flush()
            error = json.loads(process.stdout.readline())
            self.assertEqual((error['code'], error.get('placeholders')), ('invalid_configuration', ['missing']))
            paper = call('PUT', '/api/config/prompts', {**first, 'id': None, 'name': 'Paper', 'role': 'curator', 'text': '{{abstract}} / {{description}}'})
            rendered_paper = call('POST', '/api/config/render', {'id': paper['id'], 'media': 'paper',
                                 'values': {'title': 'T', 'abstract': '{{title}}'}})
            self.assertEqual(rendered_paper['text'], '{{title}} / {{title}}')
            paper = call('PUT', '/api/config/prompts', {**paper, 'text': '{{tag_schema}}'})
            process.stdin.write(json.dumps({'id': 98, 'token': token, 'method': 'POST', 'path': '/api/config/render',
                'body': {'id': paper['id'], 'media': 'paper', 'values': {'tag_schema': 'caller schema'}}}) + '\n')
            process.stdin.flush()
            self.assertEqual(json.loads(process.stdout.readline())['placeholders'], ['tag_schema'])
            for media in ('news', 'paper'):
                target_id = paper['id'] if media == 'news' else template['id']
                call('PUT', '/api/config/prompts', {**(paper if media == 'news' else template), 'text': '{{abstract}}'})
                process.stdin.write(json.dumps({'id': 2, 'token': token, 'method': 'POST', 'path': '/api/config/render',
                    'body': {'id': target_id, 'media': media, 'values': {'title': 'T', 'abstract': 'wrong'}}}) + '\n')
                process.stdin.flush()
                self.assertEqual(json.loads(process.stdout.readline())['code'], 'invalid_configuration')
            renamed = call('PUT', '/api/config/prompts', {**first, 'name': 'Renamed', 'target': 'b'})
            self.assertEqual(renamed['versionId'], first['versionId'])
            changed = call('PUT', '/api/config/prompts', {**renamed, 'text': 'Revised'})
            self.assertEqual((bound['versionId'], bound['target']), (first['versionId'], 'a'))
            changed = call('PUT', '/api/config/prompts', {**changed, 'titleLanguage': 'chinese', 'typography': 'chinese'})
            history = call('GET', '/api/config/history', {'id': first['id']})
            self.assertEqual([x['id'] for x in history['versions']], [changed['versionId'], first['versionId']])
            self.assertEqual(call('GET', '/api/config/history', {'id': first['id'], 'versionId': first['versionId']})['text'], 'Original')
            copy = call('POST', '/api/config/copy', {'id': first['id'], 'name': 'Independent',
                                                     'configuration': {**changed, 'text': 'Copy edits'}})
            self.assertNotEqual(copy['id'], first['id'])
            self.assertEqual((copy['text'], copy['target'], copy['titleLanguage'], copy['typography']), ('Copy edits', 'b', 'chinese', 'chinese'))
            restored = call('POST', '/api/config/restore', {'id': first['id'], 'versionId': first['versionId'],
                          'configuration': {**changed, 'target': 'a', 'typography': 'preserve'}})
            self.assertEqual((restored['text'], restored['target'], restored['titleLanguage'], restored['typography']), ('Original', 'a', 'chinese', 'preserve'))
            self.assertNotEqual(restored['versionId'], first['versionId'])
            self.assertEqual(call('POST', '/api/config/restore', {'id': first['id'], 'versionId': first['versionId']})['versionId'], restored['versionId'])
            reference = call('PUT', '/api/config/references', {'sourceId': 'synthetic-source', 'name': 'Source A',
                                                               'role': 'editor', 'promptId': first['id']})
            self.assertEqual(call('GET', '/api/config/references', {'promptId': first['id']})['references'], [reference])
            for number in range(101):
                call('PUT', '/api/config/references', {'sourceId': f'source-{number}', 'name': f'Name {number}',
                                                        'role': 'editor', 'promptId': first['id']})
            reference_page = call('GET', '/api/config/references', {'promptId': first['id']})
            second_page = call('GET', '/api/config/references', {'promptId': first['id'], 'after': reference_page['next']})
            self.assertEqual(len(reference_page['references']) + len(second_page['references']), 102)
            self.assertIsNone(second_page['next'])
            self.assertEqual(call('GET', '/api/config/references', {'promptId': copy['id']})['references'], [])
            process.stdin.write(json.dumps({'id': 2, 'token': token, 'method': 'DELETE', 'path': '/api/config/services',
                                            'body': {'id': service['id']}}) + '\n')
            process.stdin.flush()
            self.assertEqual(json.loads(process.stdout.readline())['code'], 'invalid_configuration')
            process.stdin.write(json.dumps({'id': 2, 'token': token, 'method': 'DELETE', 'path': '/api/config/prompts',
                                            'body': {'id': first['id']}}) + '\n')
            process.stdin.flush()
            self.assertEqual(json.loads(process.stdout.readline())['code'], 'invalid_configuration')
            for row in reference_page['references'] + second_page['references']:
                call('DELETE', '/api/config/references', {'id': row['id']})
            call('DELETE', '/api/config/prompts', {'id': first['id']})
            self.assertEqual(call('GET', '/api/config/prompts', {'id': copy['id']})['text'], 'Copy edits')
            self.assertEqual([row['kit'] for row in call('GET', '/api/config/legacy', {})['prompts']], ['legacy-kit'])
            paged = call('PUT', '/api/config/prompts', {**copy, 'id': None, 'name': 'Paged', 'text': 'v0'})
            expected = [paged['versionId']]
            for number in range(1, 102):
                paged = call('PUT', '/api/config/prompts', {**paged, 'text': f'v{number}'})
                expected.append(paged['versionId'])
            first_page = call('GET', '/api/config/history', {'id': paged['id']})
            next_page = call('GET', '/api/config/history', {'id': paged['id'], 'before': first_page['next']})
            self.assertEqual([row['id'] for row in first_page['versions'] + next_page['versions']], expected[::-1])
            self.assertIsNone(next_page['next'])

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
            reference = session([request(13, 'PUT', '/api/config/references', {'sourceId': 'synthetic',
                'name': 'Fixture source', 'role': 'curator', 'promptId': saved['id']})])[0]['result']
            references = session([request(14, 'GET', '/api/config/references', {'promptId': saved['id']})])[0]['result']
            self.assertEqual(references['references'], [reference])
            history, version, copied = session([
                request(8, 'GET', '/api/config/history', {'id': saved['id']}),
                request(9, 'GET', '/api/config/history', {'id': saved['id'], 'versionId': saved['versionId']}),
                request(10, 'POST', '/api/config/copy', {'id': saved['id'], 'name': 'Boundary copy'})])
            self.assertEqual(history['result']['versions'][0]['id'], saved['versionId'])
            self.assertEqual(version['result']['text'], text)
            self.assertEqual(copied['result']['text'], text)
            session([request(11, 'PUT', '/api/config/prompts', {**reply, 'text': 'Changed'})])
            restored = session([request(12, 'POST', '/api/config/restore', {'id': saved['id'], 'versionId': saved['versionId']})])[0]['result']
            self.assertEqual((restored['text'], restored['serviceId'], restored['target']), (text, service['id'], 'route/Exact'))
            reply = restored
            rejected, readback, status = session([
                request(4, 'PUT', '/api/config/prompts', {**reply, 'text': text + 'x'}),
                request(5, 'GET', '/api/config/prompts', {'id': saved['id']}),
                request(6, 'GET', '/api/status', {})])
            self.assertEqual(rejected['code'], 'invalid_configuration')
            self.assertEqual(readback['result'], reply)
            self.assertEqual(status['result']['schemaVersion'], 41)
