import json
from contextlib import closing
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest


class PackagedServiceTest(unittest.TestCase):
    def test_older_schema_startup_preserves_historical_rows_and_file_references(self):
        engine = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / 'data'
            command = [sys.executable, str(engine / 'stdio_service.py'), str(data)]
            bootstrap = json.dumps({'token': 'a' * 32}) + '\n'
            env = {'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'}
            first = subprocess.run(command, input=bootstrap, text=True, capture_output=True,
                                   timeout=10, env=env, cwd=directory)
            self.assertEqual(first.returncode, 0, first.stderr)
            database = data / 'information.sqlite'
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("UPDATE schema_meta SET value='40' WHERE key='schema_version'")
                db.execute('CREATE TABLE human_final (content TEXT)')
                db.execute("INSERT INTO human_final VALUES ('synthetic human work')")
                db.execute('CREATE TABLE observation_inputs (body TEXT)')
                db.execute("INSERT INTO observation_inputs VALUES ('synthetic observed body')")
                db.execute('ALTER TABLE editor_drafts ADD COLUMN artifact_path TEXT')
                db.execute("INSERT INTO editor_drafts(id,created_at,artifact_path) VALUES ('legacy','now','relative/draft.md')")
            before = database.read_bytes()
            refused = subprocess.run(command, input=bootstrap, text=True, capture_output=True,
                                     timeout=10, env=env, cwd=directory)
            self.assertNotEqual(refused.returncode, 0)
            with closing(sqlite3.connect(database)) as db:
                self.assertEqual(db.execute('SELECT content FROM human_final').fetchone(), ('synthetic human work',))
                self.assertEqual(db.execute('SELECT body FROM observation_inputs').fetchone(), ('synthetic observed body',))
                self.assertEqual(db.execute('SELECT artifact_path FROM editor_drafts').fetchone(), ('relative/draft.md',))
                self.assertEqual(db.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone(), ('40',))
            self.assertEqual(database.read_bytes(), before)

    def test_relocated_real_schema_settings_and_preservation(self):
        engine = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            payload = root / 'relocated'
            shutil.copytree(engine / '.prepared', payload, symlinks=True)
            data = root / 'data'
            token = 'a' * 32
            def run(requests):
                command = [str(payload / 'python/bin/python3'), str(payload / 'stdio_service.py'), str(data)]
                p = subprocess.run(command, input=''.join(json.dumps(x) + '\n' for x in requests),
                                   text=True, capture_output=True, timeout=30, check=True, cwd=root,
                                   env={'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'})
                return [json.loads(line) for line in p.stdout.splitlines()]
            first = run([{'token': token}, {'id': 8, 'token': 'wrong', 'method': 'GET', 'path': '/api/jobs'},
                         {'id': 9, 'token': token, 'method': 'GET', 'path': '/unknown'},
                         {'id': 1, 'token': token, 'method': 'GET', 'path': '/api/jobs'},
                         {'id': 2, 'token': token, 'method': 'PUT', 'path': '/api/settings/processing', 'body': {'processors': 3}}])
            self.assertEqual(first[0], {'status': 'ready'})
            self.assertEqual(first[1]['error'], 'unauthorized')
            self.assertEqual(first[2]['error'], 'invalid operation')
            self.assertEqual(first[3]['result']['jobs'], [])
            self.assertEqual(first[4]['result']['processors'], 3)
            with sqlite3.connect(data / 'information.sqlite') as db:
                self.assertEqual(db.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone(), ('41',))
                names = {x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertTrue({'items', 'feeds', 'body_versions', 'processing_jobs', 'app_settings', 'editor_drafts'} <= names)
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news','Synthetic','2026','2026','2026','2026')")
                db.execute("INSERT INTO raw_snapshots(id,item_id,path,source_hash,retrieved_at,created_at) VALUES (1,'item','relative','hash','2026','2026')")
                db.execute("INSERT INTO body_versions(snapshot_id,item_id,sha256,characters,authority,source,retrieved_at,stored_at) VALUES (1,'item','hash',0,'imported','fixture','2026','2026')")
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,error) VALUES ('job','item','curator','key','failed','2026','2026','2026','timeout')")
                db.execute('CREATE TABLE future_data (value TEXT)')
                db.execute("INSERT INTO future_data VALUES ('preserved')")
            second = run([{'token': token}, {'id': 3, 'token': token, 'method': 'GET', 'path': '/api/settings/processing'}, {'id': 4, 'token': token, 'method': 'GET', 'path': '/api/jobs'}])
            self.assertEqual(second[1]['result']['processors'], 3)
            self.assertEqual(second[2]['result']['jobs'][0]['id'], 'job')
            self.assertFalse(second[2]['result']['jobs'][0]['retryable'])
            with sqlite3.connect(data / 'information.sqlite') as db:
                self.assertEqual(db.execute('SELECT value FROM future_data').fetchone(), ('preserved',))
                self.assertEqual(db.execute('SELECT authority FROM body_versions').fetchone(), ('imported',))
                db.execute("UPDATE schema_meta SET value='999' WHERE key='schema_version'")
            with self.assertRaises(subprocess.CalledProcessError):
                run([{'token': token}])
            with sqlite3.connect(data / 'information.sqlite') as db:
                self.assertEqual(db.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone(), ('999',))
                self.assertEqual(db.execute('SELECT value FROM future_data').fetchone(), ('preserved',))
