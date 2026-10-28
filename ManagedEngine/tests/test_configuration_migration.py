"""Synthetic legacy data exercised through the authenticated migration commands."""
import json
import base64
from contextlib import closing
from pathlib import Path
import sqlite3
import uuid
import subprocess
import sys
import tempfile
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread


class MigrationTest(unittest.TestCase):
    def test_queued_save_receipt_survives_restart_and_rolls_back_with_save(self):
        class Directory(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200); self.end_headers(); self.wfile.write(b'{"data":[{"id":"model"}]}')
            def log_message(self, *_): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Directory)
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        self.addCleanup(server.server_close); self.addCleanup(thread.join); self.addCleanup(server.shutdown)
        script = Path(__file__).resolve().parents[1] / 'stdio_service.py'
        token = 'r' * 32
        with tempfile.TemporaryDirectory() as root:
            def start():
                p = subprocess.Popen([sys.executable, '-B', str(script), root], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
                def cleanup():
                    if not p.stdin.closed: p.stdin.close()
                    if not p.stdout.closed: p.stdout.close()
                    p.wait(timeout=30)
                self.addCleanup(cleanup)
                p.stdin.write(json.dumps({'token': token}) + '\n'); p.stdin.flush()
                self.assertEqual(json.loads(p.stdout.readline()), {'status': 'ready'})
                return p
            p = start()
            def call(path, body, method='POST', mutation_id=None):
                message = {'id': 1, 'token': token, 'method': method, 'path': path, 'body': body}
                if mutation_id: message['mutationId'] = mutation_id
                p.stdin.write(json.dumps(message) + '\n'); p.stdin.flush()
                return json.loads(p.stdout.readline())
            database = Path(root) / 'information.sqlite'
            with closing(sqlite3.connect(database)) as lock:
                lock.execute('BEGIN IMMEDIATE')
                call('/api/config/migration/preview', {'serviceId': 'missing', 'cooperative': True})
                queued = call('/api/config/services', {'name': 'Saved', 'type': 'magpie', 'endpoint': 'http://127.0.0.1:9'}, 'PUT')['result']['_pendingMutation']
                lock.rollback()
            while True:
                with closing(sqlite3.connect(database)) as db:
                    receipt = db.execute('SELECT value FROM app_settings WHERE key=?', ('nonews.mutation-receipt.' + queued,)).fetchone()
                if receipt: break
                time.sleep(.01)
            saved = json.loads(receipt[0])['result']
            p.stdin.close(); p.stdout.close(); self.assertEqual(p.wait(timeout=30), 0)
            p = start()
            recovered = call('/api/config/migration/operation', {'operationId': queued})['result']
            self.assertEqual(recovered['result'], saved)
            self.assertEqual(call('/api/config/migration/operation', {'operationId': queued})['result']['result'], saved)
            self.assertEqual(call('/api/config/services', {'id': saved['id']}, 'GET')['result'], saved)
            service = call('/api/config/services', {'name': 'Directory', 'type': 'magpie', 'endpoint': f'http://127.0.0.1:{server.server_port}'}, 'PUT')['result']
            call('/api/config/refresh', {'id': service['id']})
            with closing(sqlite3.connect(database)) as lock:
                lock.execute('BEGIN IMMEDIATE')
                call('/api/config/migration/preview', {'serviceId': 'missing', 'cooperative': True})
                prompt_id = call('/api/config/prompts', {'name': 'Exact', 'role': 'curator', 'text': '原文 {{content}}', 'serviceId': service['id'], 'target': 'model'}, 'PUT')['result']['_pendingMutation']
                lock.rollback()
            while True:
                prompt = call('/api/config/migration/operation', {'operationId': prompt_id})
                if prompt.get('result', {}).get('state') == 'complete': break
                time.sleep(.01)
            original = prompt['result']['result']
            p.stdin.close(); p.stdout.close(); self.assertEqual(p.wait(timeout=30), 0)
            p = start()
            self.assertEqual(call('/api/config/migration/operation', {'operationId': prompt_id})['result']['result'], original)
            self.assertEqual(call('/api/config/migration/operation', {'operationId': prompt_id})['result']['result']['versionId'], original['versionId'])
            retry = call('/api/config/prompts', {'name': 'Different', 'role': 'curator', 'text': 'different', 'serviceId': service['id'], 'target': 'model'}, 'PUT', mutation_id=prompt_id)['result']['_pendingMutation']
            while True:
                response = call('/api/config/migration/operation', {'operationId': retry})['result']
                if response['state'] == 'complete': break
                time.sleep(.01)
            self.assertEqual(response['result'], original)
            self.assertNotIn('Different', [row['name'] for row in call('/api/config/prompts', {}, 'GET')['result']['prompts']])
            with closing(sqlite3.connect(database)) as lock:
                lock.execute('BEGIN IMMEDIATE')
                call('/api/config/migration/preview', {'serviceId': 'missing', 'cooperative': True})
                cancelled_id = call('/api/config/services', {'name': 'Cancelled', 'type': 'magpie', 'endpoint': 'http://127.0.0.1:11'}, 'PUT')['result']['_pendingMutation']
                call('/api/config/migration/operation', {'operationId': cancelled_id, 'cancel': True})
                lock.rollback()
            while True:
                cancelled = call('/api/config/migration/operation', {'operationId': cancelled_id})['result']
                if cancelled['state'] != 'running': break
                time.sleep(.01)
            self.assertEqual(cancelled['state'], 'notSaved')
            self.assertNotIn('Cancelled', [row['name'] for row in call('/api/config/services', {}, 'GET')['result']['services']])
            with closing(sqlite3.connect(database)) as lock:
                lock.execute('BEGIN IMMEDIATE')
                call('/api/config/migration/preview', {'serviceId': 'missing', 'cooperative': True})
                stopped_id = call('/api/config/services', {'name': 'Stopped', 'type': 'magpie', 'endpoint': 'http://127.0.0.1:12'}, 'PUT')['result']['_pendingMutation']
                call('/api/config/migration/operation', {'operationId': stopped_id, 'cancel': True})
                p.stdin.close(); p.stdout.close()
                lock.rollback()
                self.assertEqual(p.wait(timeout=30), 0)
            p = start()
            self.assertEqual(call('/api/config/migration/operation', {'operationId': stopped_id})['result']['state'], 'notSaved')
            self.assertNotIn('Stopped', [row['name'] for row in call('/api/config/services', {}, 'GET')['result']['services']])
            acknowledged = call('/api/config/migration/ack', {'receiptId': prompt_id, 'cooperative': True})['result']['operationId']
            while True:
                response = call('/api/config/migration/ack', {'operationId': acknowledged})['result']
                if response['state'] == 'complete': break
                time.sleep(.01)
            self.assertEqual(call('/api/config/migration/operation', {'operationId': prompt_id})['result']['state'], 'unknown')
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("CREATE TRIGGER fail_receipt BEFORE INSERT ON app_settings WHEN NEW.key LIKE 'nonews.mutation-receipt.%' BEGIN SELECT RAISE(ABORT, 'injected'); END")
            with closing(sqlite3.connect(database)) as lock:
                lock.execute('BEGIN IMMEDIATE')
                call('/api/config/migration/preview', {'serviceId': 'missing', 'cooperative': True})
                failed_id = call('/api/config/services', {'name': 'Rollback', 'type': 'magpie', 'endpoint': 'http://127.0.0.1:10'}, 'PUT')['result']['_pendingMutation']
                lock.rollback()
            while True:
                failed = call('/api/config/migration/operation', {'operationId': failed_id})
                if 'error' in failed or failed.get('result', {}).get('state') != 'running': break
                time.sleep(.01)
            self.assertEqual(failed['result']['state'], 'notSaved')
            self.assertEqual(failed['result']['outcome'], 'notCommitted')
            services = call('/api/config/services', {}, 'GET')['result']['services']
            self.assertNotIn('Rollback', [row['name'] for row in services])
            with closing(sqlite3.connect(database)) as db, db:
                self.assertIsNone(db.execute('SELECT value FROM app_settings WHERE key=?', ('nonews.mutation-receipt.' + failed_id,)).fetchone())
                db.execute('DROP TRIGGER fail_receipt')
            p.stdin.close(); p.stdout.close(); self.assertEqual(p.wait(timeout=30), 0)

    def test_acknowledged_operation_failures_do_not_exhaust_queue(self):
        script = Path(__file__).resolve().parents[1] / 'stdio_service.py'
        token = 'f' * 32
        root = self.enterContext(tempfile.TemporaryDirectory())
        process = self.enterContext(subprocess.Popen([sys.executable, '-B', str(script), root],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
            env={'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'}))
        process.stdin.write(json.dumps({'token': token}) + '\n')
        process.stdin.flush()
        self.assertEqual(json.loads(process.stdout.readline()), {'status': 'ready'})
        def call(method, path, body):
            process.stdin.write(json.dumps({'id': 1, 'token': token, 'method': method,
                'path': path, 'body': body}) + '\n')
            process.stdin.flush()
            return json.loads(process.stdout.readline())
        for _ in range(40):
            started = call('POST', '/api/config/migration/preview',
                {'serviceId': 'missing-service', 'cooperative': True})
            self.assertIn('result', started)
            cursor = {'operationId': started['result']['operationId']}
            deadline = time.monotonic() + 5
            while True:
                response = call('POST', '/api/config/migration/preview', cursor)
                if 'error' in response:
                    break
                self.assertLess(time.monotonic(), deadline, 'Operation did not finish')
                time.sleep(.001)
            self.assertEqual(response['code'], 'invalid_configuration')
            self.assertEqual(call('POST', '/api/config/migration/preview', cursor), response)
        for _ in range(40):
            started = call('POST', '/api/config/migration/preview', {'serviceId': 'missing-service', 'cooperative': True})['result']
            cursor = {'operationId': started['operationId']}
            call('POST', '/api/config/migration/preview', {**cursor, 'cancel': True})
            while True:
                response = call('POST', '/api/config/migration/preview', cursor)
                if 'error' in response: break
                time.sleep(.001)
            self.assertIn(response['code'], {'snapshot_expired', 'invalid_configuration'})
        self.assertEqual(call('GET', '/api/status', {})['result']['schemaVersion'], 41)
        self.assertEqual(call('PUT', '/api/settings/processing', {'processors': 2})['result']['processors'], 2)

    def test_report_over_16_mib_survives_restart_and_concurrent_changes(self):
        class Directory(BaseHTTPRequestHandler):
            def do_GET(self):
                data = b'{"data":[{"id":"old/model"}]}'
                self.send_response(200)
                self.end_headers()
                self.wfile.write(data)
            def log_message(self, *_): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Directory)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        script = Path(__file__).resolve().parents[1] / 'stdio_service.py'
        token = 'e' * 32
        with tempfile.TemporaryDirectory() as root:
            def start():
                process = subprocess.Popen([sys.executable, str(script), root], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    text=True, env={'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'})
                def cleanup():
                    if process.stdin and not process.stdin.closed:
                        process.stdin.close()
                    if process.stdout and not process.stdout.closed:
                        process.stdout.close()
                    process.wait(timeout=30)
                self.addCleanup(cleanup)
                process.stdin.write(json.dumps({'token': token}) + '\n')
                process.stdin.flush()
                self.assertEqual(json.loads(process.stdout.readline()), {'status': 'ready'})
                return process
            process = start()
            def call(method, path, body):
                process.stdin.write(json.dumps({'id': 1, 'token': token, 'method': method, 'path': path, 'body': body}) + '\n')
                process.stdin.flush()
                return json.loads(process.stdout.readline())
            def finish(action, started):
                for _ in range(3000):
                    response = call('POST', '/api/config/migration/' + action, {'operationId': started['operationId']})
                    if 'error' in response:
                        return response
                    if response['result']['state'] == 'complete':
                        return response['result']['result']
                    self.assertEqual(call('GET', '/api/status', {})['result']['schemaVersion'], 41)
                    self.assertEqual(call('GET', '/api/config/services', {'id': service['id']})['result']['id'], service['id'])
                    time.sleep(.01)
                self.fail('Migration operation did not finish')
            service = call('PUT', '/api/config/services', {'name': 'Gateway', 'type': 'magpie',
                'endpoint': f'http://127.0.0.1:{server.server_port}'})['result']
            call('POST', '/api/config/refresh', {'id': service['id']})
            template = call('PUT', '/api/config/prompts', {'name': 'Render', 'role': 'curator', 'text': '{{content}}' * 7,
                'serviceId': service['id'], 'target': 'old/model'})['result']
            database = Path(root) / 'information.sqlite'
            suffix = 'x' * 8_000
            with closing(sqlite3.connect(database)) as db, db:
                db.executemany('INSERT INTO model_configs VALUES (?, ?, ?, ?)',
                    ((f'large-{index:04}-' + suffix, 'curator', '{"provider":"old","model":"model"}', 'now') for index in range(2_200)))
                db.execute('INSERT INTO app_settings VALUES (?,?,?)', ('magpie_migration_evidence',
                    json.dumps([{'text': 'literal ], { and "quote"', 'values': [1, {'nested': '值'}]}, {'old': None}]), 'now'))
            started = call('POST', '/api/config/migration/preview', {'serviceId': service['id'], 'browse': True, 'cooperative': True})['result']
            self.assertEqual(started['state'], 'running')
            queued_render = call('POST', '/api/config/render', {'id': template['id'], 'media': 'news',
                'values': {'content': 'x' * 187_230}})['result']
            self.assertIn('_pendingMutation', queued_render)
            queued_overflow = call('POST', '/api/config/render', {'id': template['id'], 'media': 'news',
                'values': {'content': '😀' * 15_605}})['result']
            self.assertIn('_pendingMutation', queued_overflow)
            queued = call('PUT', '/api/settings/processing', {'processors': 2})['result']
            self.assertIn('_pendingMutation', queued)
            progress = finish('preview', started)
            rendered = finish('operation', {'operationId': queued_render['_pendingMutation']})
            self.assertEqual(rendered['text'], 'x' * (187_230 * 7))
            self.assertEqual(finish('operation', {'operationId': queued_overflow['_pendingMutation']})['code'], 'render_too_large')
            self.assertEqual(progress['counts']['models'], 2200)
            repeated = call('POST', '/api/config/migration/preview', {'operationId': started['operationId']})['result']
            self.assertEqual(repeated['result']['snapshotId'], progress['snapshotId'])
            changed = finish('operation', {'operationId': queued['_pendingMutation']})
            self.assertEqual(changed['processors'], 2)
            self.assertEqual(call('GET', '/api/settings/processing', {})['result']['processors'], 2)
            unpublished = call('POST', '/api/config/migration/preview', {'serviceId': service['id'], 'browse': True, 'cooperative': True})['result']
            with closing(sqlite3.connect(database)) as db:
                before_cancel = {row[0] for row in db.execute("SELECT key FROM app_settings WHERE key LIKE 'nonews.migration-snapshot.%.count'")}
            deadline = time.monotonic() + 10
            while True:
                with closing(sqlite3.connect(database)) as db:
                    roots = {row[0] for row in db.execute("SELECT key FROM app_settings WHERE key LIKE 'nonews.migration-snapshot.%.count'")}
                if roots - before_cancel:
                    break
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.01)
            cancellation = call('POST', '/api/config/migration/preview', {'operationId': unpublished['operationId'], 'cancel': True})
            if 'code' not in cancellation:
                cancellation = finish('preview', unpublished)
            self.assertEqual(cancellation['code'], 'snapshot_expired')
            for _ in range(1000):
                with closing(sqlite3.connect(database)) as db:
                    roots = {row[0] for row in db.execute("SELECT key FROM app_settings WHERE key LIKE 'nonews.migration-snapshot.%.count'")}
                if roots == before_cancel:
                    break
                time.sleep(.01)
            self.assertEqual(roots, before_cancel)
            stale = call('POST', '/api/config/migration/preview', {'serviceId': service['id'], 'browse': True, 'cooperative': True})['result']
            cancelled = call('POST', '/api/config/migration/preview', {'operationId': stale['operationId'], 'cancel': True})
            if cancelled.get('result', {}).get('state') == 'complete':
                old_snapshot = cancelled['result']['result']['snapshotId']
                call('POST', '/api/config/migration/release', {'snapshotId': old_snapshot})
            elif 'error' in cancelled:
                self.assertEqual(cancelled['code'], 'snapshot_expired')
            else:
                refused = finish('preview', stale)
                self.assertEqual(refused['code'], 'snapshot_expired')
            superseded = call('POST', '/api/config/migration/preview', {'serviceId': service['id'], 'browse': True, 'cooperative': True})['result']
            replacement = call('POST', '/api/config/migration/preview', {'serviceId': service['id'], 'browse': True, 'cooperative': True})['result']
            old_result = finish('preview', superseded)
            if 'code' in old_result:
                self.assertEqual(old_result['code'], 'snapshot_expired')
            else:
                call('POST', '/api/config/migration/release', {'snapshotId': old_result['snapshotId']})
            new_report = finish('preview', replacement)
            self.assertEqual(new_report['counts']['models'], 2200)
            call('POST', '/api/config/migration/release', {'snapshotId': new_report['snapshotId']})
            release = call('POST', '/api/config/migration/release', {'snapshotId': progress['snapshotId'], 'cooperative': True})['result']
            self.assertTrue(finish('release', release)['released'])
            first = call('POST', '/api/config/migration/preview', {'serviceId': service['id']})
            self.assertIn('result', first)
            first = first['result']
            self.assertIsNotNone(first['next'])
            retry = call('POST', '/api/config/migration/preview', first['next'])['result']
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("INSERT INTO model_configs VALUES ('later','curator','{\"provider\":\"old\",\"model\":\"model\"}','now')")
                db.execute("UPDATE app_settings SET value='[{\"broken\":1},]' WHERE key='magpie_migration_evidence'")
            refusal = call('POST', '/api/config/migration/preview', {'serviceId': service['id']})
            self.assertEqual(refusal['code'], 'invalid_configuration')
            self.assertEqual(call('GET', '/api/status', {})['result']['schemaVersion'], 41)
            self.assertEqual(call('POST', '/api/config/migration/preview', first['next'])['result'], retry)
            with closing(sqlite3.connect(database)) as db, db:
                db.execute('UPDATE app_settings SET value=? WHERE key=?',
                    (json.dumps([{'text': 'literal ], { and "quote"', 'values': [1, {'nested': '值'}]}, {'old': None}]), 'magpie_migration_evidence'))
            process.stdin.close()
            process.stdout.close()
            self.assertEqual(process.wait(timeout=30), 0)
            process = start()
            self.assertEqual(call('POST', '/api/config/migration/preview', first['next'])['result'], retry)
            chunks = [base64.b64decode(first['chunk'])]
            cursor = first['next']
            while cursor is not None:
                page = call('POST', '/api/config/migration/preview', cursor)['result']
                chunks.append(base64.b64decode(page['chunk']))
                cursor = page['next']
            encoded = b''.join(chunks)
            self.assertGreater(len(encoded), 16 * 1024 * 1024)
            report = json.loads(encoded)
            self.assertEqual(len(report['models']), 2_200)
            self.assertEqual(report['models'][0]['kit'], 'large-0000-' + suffix)
            self.assertEqual(report['models'][-1]['kit'], 'large-2199-' + suffix)
            self.assertEqual(report['evidence'], [{'text': 'literal ], { and "quote"', 'values': [1, {'nested': '值'}]}, {'old': None}])
            browse = call('POST', '/api/config/migration/preview', {'serviceId': service['id'], 'browse': True})['result']
            self.assertEqual(browse['counts']['models'], 2201)
            self.assertEqual(browse['counts']['evidence'], 2)
            first_record = call('POST', '/api/config/migration/preview',
                {'snapshotId': browse['snapshotId'], 'section': 'models', 'index': 0, 'part': 0})['result']
            self.assertEqual(json.loads(base64.b64decode(first_record['chunk']))['kit'], 'large-0000-' + suffix)
            self.assertEqual(first_record, call('POST', '/api/config/migration/preview',
                {'snapshotId': browse['snapshotId'], 'section': 'models', 'index': 0, 'part': 0})['result'])
            last_record = call('POST', '/api/config/migration/preview',
                {'snapshotId': browse['snapshotId'], 'section': 'models', 'index': 2200, 'part': 0})['result']
            self.assertEqual(json.loads(base64.b64decode(last_record['chunk']))['kit'], 'later')
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("DELETE FROM model_configs WHERE kit_id='later'")
            process.stdin.close()
            process.stdout.close()
            self.assertEqual(process.wait(timeout=30), 0)
            process = start()
            self.assertEqual(last_record, call('POST', '/api/config/migration/preview',
                {'snapshotId': browse['snapshotId'], 'section': 'models', 'index': 2200, 'part': 0})['result'])
            for index in range(2201):
                item = call('POST', '/api/config/migration/preview',
                    {'snapshotId': browse['snapshotId'], 'section': 'models', 'index': index, 'part': 0})['result']
                expected = 'later' if index == 2200 else f'large-{index:04}-' + suffix
                self.assertEqual(json.loads(base64.b64decode(item['chunk']))['kit'], expected)
            self.assertTrue(call('POST', '/api/config/migration/release', {'snapshotId': browse['snapshotId']})['result']['released'])
            self.assertEqual(call('POST', '/api/config/migration/preview',
                {'snapshotId': browse['snapshotId'], 'section': 'models', 'index': 0, 'part': 0})['code'], 'snapshot_expired')
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("INSERT INTO model_configs VALUES ('later','curator','{\"provider\":\"old\",\"model\":\"model\"}','now')")
            legacy = json.dumps(report['evidence'])
            self.assertTrue(call('POST', '/api/config/migration/pause', {})['result']['paused'])
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("CREATE TRIGGER fail_resume BEFORE UPDATE ON app_settings WHEN NEW.key='magpie_claims_paused' AND NEW.value='0' BEGIN SELECT RAISE(ABORT, 'injected'); END")
            failed = call('POST', '/api/config/migration/apply', {'serviceId': service['id'], 'cooperative': True})['result']
            self.assertEqual(finish('apply', failed)['error'], 'operation failed')
            self.assertEqual(call('GET', '/api/status', {})['result']['schemaVersion'], 41)
            with closing(sqlite3.connect(database)) as db, db:
                self.assertEqual(db.execute("SELECT count(*) FROM app_settings WHERE key LIKE 'nonews.migration-evidence.%'").fetchone()[0], 0)
                self.assertEqual(db.execute("SELECT count(*) FROM model_configs WHERE config_json LIKE '%target%'").fetchone()[0], 0)
                self.assertEqual(db.execute("SELECT value FROM app_settings WHERE key='magpie_claims_paused'").fetchone()[0], '1')
                db.execute('DROP TRIGGER fail_resume')
            started_apply = call('POST', '/api/config/migration/apply', {'serviceId': service['id'], 'cooperative': True})['result']
            queued = call('PUT', '/api/settings/processing', {'processors': 3})['result']
            self.assertIn('_pendingMutation', queued)
            applied = finish('apply', started_apply)
            self.assertEqual(applied['status'], 'applied')
            self.assertEqual(applied['operationId'], started_apply['operationId'])
            self.assertEqual(finish('operation', {'operationId': queued['_pendingMutation']})['processors'], 3)
            self.assertLess(len(json.dumps(applied)), 1024)
            with closing(sqlite3.connect(database)) as db:
                self.assertEqual(db.execute("SELECT value FROM app_settings WHERE key='magpie_migration_evidence'").fetchone()[0], legacy)
            process.stdin.close()
            process.stdout.close()
            self.assertEqual(process.wait(timeout=30), 0)
            process = start()
            after = call('POST', '/api/config/migration/preview', {'serviceId': service['id']})['result']
            chunks = [base64.b64decode(after['chunk'])]
            cursor = after['next']
            while cursor is not None:
                page = call('POST', '/api/config/migration/preview', cursor)['result']
                chunks.append(base64.b64decode(page['chunk']))
                cursor = page['next']
            after_report = json.loads(b''.join(chunks))
            self.assertEqual(after_report['lastApply'], applied)
            self.assertEqual(after_report['evidence'][:2], report['evidence'])
            self.assertEqual([row['kit'] for row in after_report['evidence'][2:]],
                             [row['kit'] for row in after_report['models']])
            self.assertEqual(len(after_report['evidence']), 2203)
            call('POST', '/api/config/migration/pause', {})
            self.assertEqual(call('POST', '/api/config/migration/apply', {'serviceId': service['id']})['result']['status'], 'applied')
            after_again = call('POST', '/api/config/migration/preview', {'serviceId': service['id']})['result']
            chunks = [base64.b64decode(after_again['chunk'])]
            cursor = after_again['next']
            while cursor is not None:
                page = call('POST', '/api/config/migration/preview', cursor)['result']
                chunks.append(base64.b64decode(page['chunk']))
                cursor = page['next']
            self.assertEqual(json.loads(b''.join(chunks))['evidence'], after_report['evidence'])
            process.stdin.close()
            process.stdout.close()
            self.assertEqual(process.wait(timeout=30), 0)

    def test_pause_wait_apply_preserves_completed_and_pinned_editor(self):
        class Directory(BaseHTTPRequestHandler):
            def do_GET(self):
                content = b'{"data":[{"id":"old/model"},{"id":"editor/new"},{"id":"route/A"},{"id":"route/B"},{"id":"explicit/target"}]}'
                self.send_response(200)
                self.end_headers()
                self.wfile.write(content)
            def log_message(self, *_): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Directory)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        script = Path(__file__).resolve().parents[1] / 'stdio_service.py'
        token = 'd' * 32
        with tempfile.TemporaryDirectory() as root:
            def session(requests):
                command = [sys.executable, str(script), root]
                process = subprocess.run(command, input=''.join(json.dumps(x) + '\n' for x in [{'token': token}, *requests]),
                    text=True, capture_output=True, timeout=30, env={'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'})
                self.assertEqual(process.returncode, 0, process.stderr)
                return [json.loads(x) for x in process.stdout.splitlines()][1:]
            def call(number, path, body):
                return {'id': number, 'token': token, 'method': 'POST', 'path': path, 'body': body}
            service = session([{'id': 1, 'token': token, 'method': 'PUT', 'path': '/api/config/services',
                'body': {'name': 'Gateway', 'type': 'magpie', 'endpoint': f'http://127.0.0.1:{server.server_port}'}}])[0]['result']
            other = session([{'id': 1, 'token': token, 'method': 'PUT', 'path': '/api/config/services',
                'body': {'name': 'Other Gateway', 'type': 'magpie', 'endpoint': f'http://127.0.0.1:{server.server_port}'}}])[0]['result']
            session([call(2, '/api/config/refresh', {'id': service['id']})])
            session([call(2, '/api/config/refresh', {'id': other['id']})])
            database = Path(root) / 'information.sqlite'
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("INSERT INTO model_configs VALUES ('news','curator',?, 'now')", (json.dumps({'provider': 'old', 'model': 'model'}),))
                db.execute("INSERT INTO model_configs VALUES ('news','editor',?, 'now')", (json.dumps({'provider': 'old', 'model': 'other'}),))
                db.execute("INSERT INTO model_configs VALUES ('paper','curator',?, 'now')", (json.dumps({'target': 'missing/route'}),))
                db.execute("INSERT INTO model_configs VALUES ('alpha','curator',?, 'now')", (json.dumps({'provider': 'old', 'model': 'model', 'target': 'route/A'}),))
                db.execute("INSERT INTO model_configs VALUES ('beta','curator',?, 'now')", (json.dumps({'provider': 'old', 'model': 'model', 'target': 'missing/route'}),))
                db.execute("INSERT INTO model_configs VALUES ('unsupported','curator',?, 'now')", (json.dumps({'provider': 'old', 'model': 'model', 'api_key': 'synthetic-private-value'}),))
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news','Synthetic','now','now','now','now')")
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('paper','paper','Synthetic','now','now','now','now')")
                db.execute("INSERT INTO feeds(id,freshrss_feed_id,title,first_seen_at,last_seen_at) VALUES ('feed','feed','Feed','now','now')")
                db.execute("INSERT INTO entry_observations(freshrss_entry_id,feed_id,item_id,ingested_at) VALUES ('obs','feed','item','now')")
                db.execute("INSERT INTO ai_feed_settings(freshrss_feed_id,media_type,kit_id,last_seen_at,updated_at) VALUES ('feed',NULL,'wrong','now','now')")
                db.execute("INSERT INTO ai_kits(id,name,content_type,threshold,created_at,updated_at) VALUES ('news','News','news',7,'now','now')")
                db.execute("INSERT INTO item_feed_contracts(item_id,media_type,kit_id,pinned_at) VALUES ('item','news','news','now')")
                for ident, status, stage, pinned in [('running', 'running', 'curator', None), ('pending', 'pending', 'editor', 'explicit/target'), ('proven', 'pending', 'editor', 'explicit/target'), ('done', 'succeeded', 'editor', None)]:
                    db.execute('INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,editor_target) VALUES (?,?,?,?,?,?,?,?,?)',
                               (ident, 'item', stage, ident, status, 'now', 'now', 'now', pinned))
                db.execute("UPDATE processing_jobs SET origin='automatic' WHERE id='pending'")
                db.execute("UPDATE processing_jobs SET origin='automatic' WHERE id='proven'")
                proven_id = uuid.uuid5(uuid.NAMESPACE_URL, 'proven').hex
                db.execute('INSERT INTO app_settings VALUES (?,?,?)', ('nonews.migration-job.' + proven_id,
                    json.dumps({'id': proven_id, 'jobId': 'proven', 'target': 'explicit/target',
                                'serviceId': other['id'], 'endpoint': other['endpoint']}), 'now'))
                db.execute("INSERT INTO pipeline_stage_runs VALUES ('pending','item','editor','pending',?, 'now')", (json.dumps({'model': 'historic'}),))
                db.execute("INSERT INTO pipeline_stage_runs VALUES ('pending','paper','curator','pending',?, 'now')", (json.dumps({'model': 'other item'}),))
                db.execute("INSERT INTO pipeline_stage_runs VALUES ('done','item','editor','ready',?, 'now')", (json.dumps({'model': 'completed'}),))
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,origin) VALUES ('mismatch','item','curator','mismatch','pending','now','now','now','user')")
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,magpie_block_reason) VALUES ('maintenance','item','maintenance','maintenance','pending','now','now','now','existing')")
                db.execute("INSERT INTO pipeline_stage_runs VALUES ('mismatch','item','curator','pending',?, 'now')", (json.dumps({'model': 'keep'}),))
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at) VALUES ('unresolved','paper','curator','unresolved','pending','now','now','now')")
                db.execute("INSERT INTO item_feed_contracts(item_id,media_type,kit_id,pinned_at) VALUES ('paper','paper','missing-kit','now')")
                db.execute("INSERT INTO pipeline_stage_runs VALUES ('unresolved','paper','curator','pending',?, 'now')", (json.dumps({'model': 'original'}),))
            body = {'serviceId': service['id'], 'choices': {'news/editor': 'editor/new'}}
            choice_report = session([call(9, '/api/config/migration/preview', {'serviceId': service['id'],
                'choices': {'old/model': 'route/B', 'beta/curator': 'route/A'}})])[0]['result']
            choices = {row['kit']: row for row in choice_report['models'] if row['kit'] in {'alpha', 'beta'}}
            self.assertEqual((choices['alpha']['target'], choices['alpha']['basis']), ('route/B', 'explicit choice'))
            self.assertEqual((choices['beta']['target'], choices['beta']['basis']), ('route/A', 'explicit choice'))
            unsafe = next(row for row in choice_report['models'] if row['kit'] == 'unsupported')
            self.assertTrue(unsafe['blocked'])
            self.assertNotIn('synthetic-private-value', json.dumps(choice_report))
            preview, paused, waiting = session([call(3, '/api/config/migration/preview', body), call(4, '/api/config/migration/pause', {}), call(5, '/api/config/migration/apply', body)])
            self.assertEqual(preview['result']['running'], 1)
            unknown = next(row for row in preview['result']['pending'] if row['id'] == 'pending')
            self.assertIsNone(unknown['editorServiceId'])
            self.assertEqual(unknown['proposedEditorServiceId'], service['id'])
            self.assertIn('Editor service association required', unknown['blocked'])
            self.assertEqual(next(x for x in preview['result']['pending'] if x['id'] == 'pending')['kit'], 'news')
            self.assertEqual(paused['result']['paused'], True)
            self.assertEqual(waiting['result']['status'], 'waiting')
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("UPDATE processing_jobs SET status='succeeded' WHERE id='running'")
                db.execute("UPDATE ai_feed_settings SET media_type='paper' WHERE freshrss_feed_id='feed'")
            applied = session([call(6, '/api/config/migration/apply', body)])[0]['result']
            self.assertEqual(applied['status'], 'applied')
            self.assertEqual(applied['running'], 0)
            with closing(sqlite3.connect(database)) as db:
                self.assertEqual(db.execute("SELECT magpie_block_reason FROM processing_jobs WHERE id='maintenance'").fetchone()[0], 'existing')
            later = session([call(7, '/api/config/migration/preview', body)])[0]['result']
            evidence = next(row for row in later['evidence'] if row['kit'] == 'news' and row['role'] == 'curator')
            self.assertEqual((evidence['old'], evidence['target'], evidence['serviceId']),
                             ({'provider': 'old', 'model': 'model'}, 'old/model', service['id']))
            binding = next(row for row in later['models'] if row['kit'] == 'news' and row['role'] == 'curator')
            self.assertEqual(binding['serviceId'], service['id'])
            pinned = next(row for row in later['pending'] if row['id'] == 'pending')
            self.assertEqual((pinned['editorTarget'], pinned['editorServiceId']), ('explicit/target', None))
            self.assertIn('Editor service association required', pinned['blocked'])
            proven = next(row for row in later['pending'] if row['id'] == 'proven')
            self.assertEqual(proven['editorServiceId'], other['id'])
            self.assertEqual(proven['proposedEditorServiceId'], other['id'])
            conflict = session([call(28, '/api/config/migration/preview',
                {**body, 'editorServices': {'proven': service['id']}})])[0]['result']
            self.assertIn('Existing Editor association conflicts with this proposal',
                          next(row for row in conflict['pending'] if row['id'] == 'proven')['blocked'])
            explicit = {**body, 'editorServices': {'pending': service['id']}}
            reviewed = session([call(23, '/api/config/migration/preview', explicit)])[0]['result']
            self.assertEqual(next(row for row in reviewed['pending'] if row['id'] == 'pending')['proposedEditorServiceId'], service['id'])
            session([call(24, '/api/config/migration/pause', {})])
            unreviewed = session([call(25, '/api/config/migration/apply', explicit)])[0]
            self.assertEqual(unreviewed['code'], 'invalid_configuration')
            approved = {**explicit, 'reviewToken': reviewed['editorReviewToken']}
            changed = {**approved, 'choices': {**body['choices'], 'alpha/curator': 'route/B'}}
            self.assertEqual(session([call(29, '/api/config/migration/apply', changed)])[0]['code'], 'invalid_configuration')
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("UPDATE processing_jobs SET editor_target='changed/target' WHERE id='pending'")
            self.assertEqual(session([call(30, '/api/config/migration/apply', approved)])[0]['code'], 'invalid_configuration')
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("UPDATE processing_jobs SET editor_target='explicit/target' WHERE id='pending'")
            self.assertEqual(session([call(25, '/api/config/migration/apply', approved)])[0]['result']['status'], 'applied')
            later = session([call(26, '/api/config/migration/preview', body)])[0]['result']
            self.assertEqual(next(row for row in later['pending'] if row['id'] == 'pending')['editorServiceId'], service['id'])
            self.assertEqual(next(row for row in later['pending'] if row['id'] == 'proven')['editorServiceId'], other['id'])
            refused = session([{'id': 8, 'token': token, 'method': 'DELETE', 'path': '/api/config/services',
                                'body': {'id': service['id']}}])[0]
            self.assertEqual(refused['code'], 'invalid_configuration')
            refused_other = session([{'id': 27, 'token': token, 'method': 'DELETE', 'path': '/api/config/services',
                                      'body': {'id': other['id']}}])[0]
            self.assertEqual(refused_other['code'], 'invalid_configuration')
            with closing(sqlite3.connect(database)) as db, db:
                for index in range(1400):
                    db.execute('INSERT INTO model_configs VALUES (?, ?, ?, ?)',
                        (f'bulk-{index:04}-' + 'x' * 900, 'curator', json.dumps({'provider': 'old', 'model': 'model'}), 'now'))
            first = session([call(10, '/api/config/migration/preview', body)])[0]['result']
            recent = []
            for index in range(5):
                alternative = {**body, 'choices': {**body['choices'], 'alpha/curator': 'route/A' if index % 2 else 'route/B'}}
                recent.append(session([call(18, '/api/config/migration/preview', alternative)])[0]['result'])
            second, third = recent[-2:]
            expired = session([call(20, '/api/config/migration/preview', first['next'])])[0]
            self.assertEqual(expired['code'], 'snapshot_expired')
            retry1 = session([call(21, '/api/config/migration/preview', second['next'])])[0]['result']
            retry2 = session([call(22, '/api/config/migration/preview', second['next'])])[0]['result']
            self.assertEqual(retry1, retry2)
            with closing(sqlite3.connect(database)) as db:
                roots = db.execute("SELECT count(*) FROM app_settings WHERE key LIKE 'nonews.migration-snapshot.%.count'").fetchone()[0]
                stored = db.execute("SELECT sum(length(value)) FROM app_settings WHERE key LIKE 'nonews.migration-snapshot.%'").fetchone()[0]
                self.assertEqual(roots, 2)
                self.assertLess(stored, 46 * 1024 * 1024)
            self.assertTrue(session([call(31, '/api/config/migration/release', {'snapshotId': second['snapshotId']})])[0]['result']['released'])
            self.assertEqual(session([call(32, '/api/config/migration/preview', second['next'])])[0]['code'], 'snapshot_expired')
            first = third
            chunks = [base64.b64decode(first['chunk'])]
            cursor = first['next']
            while cursor is not None:
                page = session([call(11, '/api/config/migration/preview', cursor)])[0]['result']
                chunks.append(base64.b64decode(page['chunk']))
                cursor = page['next']
            full = json.loads(b''.join(chunks))
            self.assertEqual(len([row for row in full['models'] if row['kit'].startswith('bulk-')]), 1400)
            session([call(12, '/api/config/migration/pause', {})])
            large_apply = session([call(13, '/api/config/migration/apply', body)])[0]['result']
            self.assertEqual(large_apply['status'], 'applied')
            self.assertLess(len(json.dumps(large_apply)), 1024)
            after = session([call(14, '/api/config/migration/preview', body)])[0]['result']
            evidence_chunks = [base64.b64decode(after['chunk'])]
            cursor = after['next']
            while cursor is not None:
                page = session([call(15, '/api/config/migration/preview', cursor)])[0]['result']
                evidence_chunks.append(base64.b64decode(page['chunk']))
                cursor = page['next']
            report = json.loads(b''.join(evidence_chunks))
            self.assertEqual({row['id'] for row in report['pending']}, {row['id'] for row in full['pending']})
            self.assertEqual({row['kit'] for row in report['evidence'] if row['kit'].startswith('bulk-')},
                             {f'bulk-{index:04}-' + 'x' * 900 for index in range(1400)})
            with closing(sqlite3.connect(database)) as db, db:
                self.assertEqual(db.execute("SELECT editor_target FROM processing_jobs WHERE id='pending'").fetchone()[0], 'explicit/target')
                self.assertEqual(json.loads(db.execute("SELECT result_json FROM pipeline_stage_runs WHERE job_id='pending' AND item_id='item'").fetchone()[0]), {'model': 'historic'})
                self.assertEqual(json.loads(db.execute("SELECT result_json FROM pipeline_stage_runs WHERE job_id='pending' AND item_id='paper'").fetchone()[0]), {'model': 'other item'})
                self.assertEqual(json.loads(db.execute("SELECT result_json FROM pipeline_stage_runs WHERE job_id='done'").fetchone()[0]), {'model': 'completed'})
                self.assertEqual(json.loads(db.execute("SELECT result_json FROM pipeline_stage_runs WHERE job_id='unresolved'").fetchone()[0]), {'model': 'original'})
                self.assertEqual(json.loads(db.execute("SELECT result_json FROM pipeline_stage_runs WHERE job_id='mismatch'").fetchone()[0]), {'model': 'keep'})
                self.assertIn('Media mismatch', db.execute("SELECT magpie_block_reason FROM processing_jobs WHERE id='mismatch'").fetchone()[0])
                self.assertIn('Kit unavailable', db.execute("SELECT magpie_block_reason FROM processing_jobs WHERE id='unresolved'").fetchone()[0])
                self.assertEqual(json.loads(db.execute("SELECT config_json FROM model_configs WHERE kit_id='news' AND role='curator'").fetchone()[0]), {'target': 'old/model'})
                self.assertIn('synthetic-private-value', db.execute("SELECT config_json FROM model_configs WHERE kit_id='unsupported'").fetchone()[0])
                db.execute('DELETE FROM model_configs')
            guarded = session([{'id': 16, 'token': token, 'method': 'DELETE', 'path': '/api/config/services',
                                'body': {'id': service['id']}}])[0]
            self.assertEqual(guarded['code'], 'invalid_configuration')
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("UPDATE processing_jobs SET status='succeeded' WHERE id='pending'")
            removed = session([{'id': 17, 'token': token, 'method': 'DELETE', 'path': '/api/config/services',
                                'body': {'id': service['id']}}])[0]
            self.assertTrue(removed['result']['deleted'])
