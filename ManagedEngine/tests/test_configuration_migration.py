"""Synthetic legacy data exercised through the authenticated migration commands."""
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread


class MigrationTest(unittest.TestCase):
    def test_pause_wait_apply_preserves_completed_and_pinned_editor(self):
        class Directory(BaseHTTPRequestHandler):
            def do_GET(self):
                content = b'{"data":[{"id":"old/model"},{"id":"editor/new"}]}'
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
            session([call(2, '/api/config/refresh', {'id': service['id']})])
            database = Path(root) / 'information.sqlite'
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("INSERT INTO model_configs VALUES ('news','curator',?, 'now')", (json.dumps({'provider': 'old', 'model': 'model'}),))
                db.execute("INSERT INTO model_configs VALUES ('news','editor',?, 'now')", (json.dumps({'provider': 'old', 'model': 'other'}),))
                db.execute("INSERT INTO model_configs VALUES ('paper','curator',?, 'now')", (json.dumps({'target': 'missing/route'}),))
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news','Synthetic','now','now','now','now')")
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('paper','paper','Synthetic','now','now','now','now')")
                for ident, status, stage, pinned in [('running', 'running', 'curator', None), ('pending', 'pending', 'editor', 'explicit/target'), ('done', 'succeeded', 'editor', None)]:
                    db.execute('INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,editor_target) VALUES (?,?,?,?,?,?,?,?,?)',
                               (ident, 'item', stage, ident, status, 'now', 'now', 'now', pinned))
                db.execute("INSERT INTO pipeline_stage_runs VALUES ('pending','item','editor','pending',?, 'now')", (json.dumps({'model': 'historic'}),))
                db.execute("INSERT INTO pipeline_stage_runs VALUES ('pending','paper','curator','pending',?, 'now')", (json.dumps({'model': 'other item'}),))
                db.execute("INSERT INTO pipeline_stage_runs VALUES ('done','item','editor','ready',?, 'now')", (json.dumps({'model': 'completed'}),))
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at) VALUES ('unresolved','paper','curator','unresolved','pending','now','now','now')")
                db.execute("INSERT INTO pipeline_stage_runs VALUES ('unresolved','paper','curator','pending',?, 'now')", (json.dumps({'model': 'original'}),))
            body = {'serviceId': service['id'], 'choices': {'news/editor': 'editor/new'}}
            preview, paused, waiting = session([call(3, '/api/config/migration/preview', body), call(4, '/api/config/migration/pause', {}), call(5, '/api/config/migration/apply', body)])
            self.assertEqual(preview['result']['running'], 1)
            self.assertEqual(paused['result']['paused'], True)
            self.assertEqual(waiting['result']['status'], 'waiting')
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("UPDATE processing_jobs SET status='succeeded' WHERE id='running'")
            applied = session([call(6, '/api/config/migration/apply', body)])[0]['result']
            self.assertEqual(applied['status'], 'applied')
            self.assertEqual(applied['running'], 0)
            later = session([call(7, '/api/config/migration/preview', body)])[0]['result']
            evidence = next(row for row in later['evidence'] if row['kit'] == 'news' and row['role'] == 'curator')
            self.assertEqual((evidence['old'], evidence['target'], evidence['serviceId']),
                             ({'provider': 'old', 'model': 'model'}, 'old/model', service['id']))
            with closing(sqlite3.connect(database)) as db, db:
                self.assertEqual(db.execute("SELECT editor_target FROM processing_jobs WHERE id='pending'").fetchone()[0], 'explicit/target')
                self.assertEqual(json.loads(db.execute("SELECT result_json FROM pipeline_stage_runs WHERE job_id='pending' AND item_id='item'").fetchone()[0]), {'model': 'historic'})
                self.assertEqual(json.loads(db.execute("SELECT result_json FROM pipeline_stage_runs WHERE job_id='pending' AND item_id='paper'").fetchone()[0]), {'model': 'other item'})
                self.assertEqual(json.loads(db.execute("SELECT result_json FROM pipeline_stage_runs WHERE job_id='done'").fetchone()[0]), {'model': 'completed'})
                self.assertEqual(json.loads(db.execute("SELECT result_json FROM pipeline_stage_runs WHERE job_id='unresolved'").fetchone()[0]), {'model': 'original'})
                self.assertIn('paper/curator', db.execute("SELECT magpie_block_reason FROM processing_jobs WHERE id='unresolved'").fetchone()[0])
                self.assertEqual(json.loads(db.execute("SELECT config_json FROM model_configs WHERE kit_id='news' AND role='curator'").fetchone()[0]), {'target': 'old/model'})
