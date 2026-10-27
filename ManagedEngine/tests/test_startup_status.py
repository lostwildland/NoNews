import json
from contextlib import closing
import shutil
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


class StartupStatusTest(unittest.TestCase):
    def test_required_schema_semantics_are_checked_before_ready(self):
        script = Path(__file__).resolve().parents[1] / 'stdio_service.py'
        changes = {
            'primary_key': ('processing_jobs', 'id TEXT PRIMARY KEY', 'id TEXT'),
            'unique': ('processing_jobs', 'idempotency_key TEXT NOT NULL UNIQUE', 'idempotency_key TEXT NOT NULL'),
            'foreign_key': ('processing_jobs', 'item_id TEXT NOT NULL REFERENCES items(id)', 'item_id TEXT NOT NULL'),
            'not_null': ('processing_jobs', 'stage TEXT NOT NULL', 'stage TEXT'),
            'default': ('processing_jobs', 'attempts INTEGER NOT NULL DEFAULT 0', 'attempts INTEGER NOT NULL'),
            'affinity': ('processing_jobs', 'attempts INTEGER NOT NULL DEFAULT 0', 'attempts TEXT NOT NULL DEFAULT 0'),
            'rowid': ('raw_snapshots', 'id INTEGER PRIMARY KEY', 'id TEXT PRIMARY KEY'),
            'check': ('items', "CHECK(media_type IN ('news','paper','newsletter','podcast','video'))", ''),
            'generated': ('processing_jobs', 'stage TEXT NOT NULL', "stage TEXT GENERATED ALWAYS AS ('curator') VIRTUAL NOT NULL"),
            'extra_check': ('processing_jobs', 'stage TEXT NOT NULL', "stage TEXT NOT NULL CHECK(stage='never')"),
            'extra_unique': ('processing_jobs', 'stage TEXT NOT NULL', 'stage TEXT NOT NULL UNIQUE'),
            'extra_not_null': ('processing_jobs', 'error TEXT', 'error TEXT NOT NULL'),
            'extra_foreign_key': ('processing_jobs', 'error TEXT', 'error TEXT REFERENCES app_settings(key)'),
            'partial_index': None,
        }
        for defect, change in changes.items():
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temp:
                data = Path(temp) / 'data'
                def launch():
                    return subprocess.run([sys.executable, str(script), str(data)], input=json.dumps({'token':'a'*32})+'\n', text=True, capture_output=True, timeout=10)
                self.assertEqual(json.loads(launch().stdout), {'status':'ready'})
                database = data / 'information.sqlite'
                with closing(sqlite3.connect(database)) as db, db:
                    if change is None:
                        db.execute('DROP INDEX media_document_one_pending')
                    else:
                        table, old, new = change
                        definition = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()[0]
                        self.assertIn(old, definition)
                        indexes = [r[0] for r in db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL", (table,))]
                        db.execute('DROP TABLE ' + table)
                        db.execute(definition.replace(old, new, 1))
                        for index in indexes:
                            db.execute(index)
                    db.execute('CREATE TABLE future_data(value BLOB)')
                    db.execute('INSERT INTO future_data VALUES (?)', (b'preserved',))
                before = database.read_bytes()
                result = launch()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(json.loads(result.stdout), {'status':'error','code':'schema_incomplete'})
                self.assertEqual(result.stderr, '')
                self.assertEqual(database.read_bytes(), before)
                with closing(sqlite3.connect(database)) as db:
                    self.assertEqual(db.execute('SELECT value FROM future_data').fetchone(), (b'preserved',))

    def test_current_startup_preserves_empty_legacy_structures(self):
        script = Path(__file__).resolve().parents[1] / 'stdio_service.py'
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp) / 'data'
            token = 'a' * 32
            def launch():
                return subprocess.run([sys.executable, str(script), str(data)], input=json.dumps({'token': token}) + '\n',
                                      text=True, capture_output=True, timeout=10, check=True,
                                      env={'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'})
            self.assertEqual(json.loads(launch().stdout), {'status': 'ready'})
            database = data / 'information.sqlite'
            with closing(sqlite3.connect(database)) as db, db:
                for table in ('raw_texts', 'draft_texts'):
                    db.execute('CREATE TABLE ' + table + ' (snapshot_id INTEGER, text TEXT, future_field BLOB)')
                    db.execute('CREATE INDEX ' + table + '_future ON ' + table + '(future_field)')
                    db.execute('CREATE TRIGGER ' + table + '_future AFTER INSERT ON ' + table + ' BEGIN SELECT 1; END')
                before = db.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name').fetchall()
            for _ in range(2):
                self.assertEqual(json.loads(launch().stdout), {'status': 'ready'})
                with closing(sqlite3.connect(database)) as db:
                    self.assertEqual(db.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name').fetchall(), before)

    def test_schema_errors_and_corrupt_database_are_controlled(self):
        script = Path(__file__).resolve().parents[1] / 'stdio_service.py'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            token = 'a' * 32
            def launch(data):
                return subprocess.run([sys.executable, str(script), str(data)], input=json.dumps({'token': token}) + '\n',
                                      text=True, capture_output=True, timeout=10,
                                      env={'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'})
            data = root / 'data'
            self.assertEqual(json.loads(launch(data).stdout), {'status': 'ready'})
            database = data / 'information.sqlite'
            for version, code in [('40', 'schema_migration_required'), ('999', 'schema_newer')]:
                with closing(sqlite3.connect(database)) as db, db:
                    db.execute("UPDATE schema_meta SET value=? WHERE key='schema_version'", (version,))
                p = launch(data)
                self.assertNotEqual(p.returncode, 0)
                self.assertEqual(json.loads(p.stdout), {'status': 'error', 'code': code})
                self.assertEqual(p.stderr, '')
            incomplete = root / 'incomplete'
            self.assertEqual(json.loads(launch(incomplete).stdout), {'status': 'ready'})
            incomplete_db = incomplete / 'information.sqlite'
            with closing(sqlite3.connect(incomplete_db)) as db, db:
                db.execute('DROP TABLE body_versions')
                db.execute('CREATE TABLE unknown_table (value TEXT)')
                db.execute("INSERT INTO unknown_table VALUES ('keep')")
            before = incomplete_db.read_bytes()
            self.assertEqual(json.loads(launch(incomplete).stdout), {'status': 'error', 'code': 'schema_incomplete'})
            self.assertEqual(incomplete_db.read_bytes(), before)
            with closing(sqlite3.connect(incomplete_db)) as db, db:
                self.assertEqual(db.execute('SELECT value FROM unknown_table').fetchone(), ('keep',))
            missing_column = root / 'missing-column'
            self.assertEqual(json.loads(launch(missing_column).stdout), {'status': 'ready'})
            column_db = missing_column / 'information.sqlite'
            with closing(sqlite3.connect(column_db)) as db, db:
                db.execute('ALTER TABLE media_raw_activation_intents DROP COLUMN quarantine_path')
            before_column = column_db.read_bytes()
            self.assertEqual(json.loads(launch(missing_column).stdout), {'status': 'error', 'code': 'schema_incomplete'})
            self.assertEqual(column_db.read_bytes(), before_column)
            extra = root / 'extra'
            self.assertEqual(json.loads(launch(extra).stdout), {'status': 'ready'})
            with closing(sqlite3.connect(extra / 'information.sqlite')) as db, db:
                db.execute('ALTER TABLE items ADD COLUMN future_field TEXT')
                db.execute('CREATE TABLE future_extra (value TEXT)')
                db.execute('CREATE INDEX extra_future ON items(future_field)')
                db.execute('DROP INDEX media_document_one_pending')
                db.execute("CREATE UNIQUE INDEX equivalent_pending ON media_document_generations(item_id) WHERE (state = 'pending')")
            self.assertEqual(json.loads(launch(extra).stdout), {'status': 'ready'})
            corrupt = root / 'corrupt'
            corrupt.mkdir()
            (corrupt / 'information.sqlite').write_bytes(b'not a database')
            self.assertEqual(json.loads(launch(corrupt).stdout), {'status': 'error', 'code': 'data_corrupt'})
            denied = root / 'denied'
            denied.mkdir(mode=0o500)
            try:
                self.assertEqual(json.loads(launch(denied).stdout), {'status': 'error', 'code': 'data_unavailable'})
            finally:
                denied.chmod(0o700)
            blocked = root / 'not-a-directory'
            blocked.write_text('x')
            self.assertEqual(json.loads(launch(blocked).stdout), {'status': 'error', 'code': 'data_unavailable'})
            fixture = root / 'fixture'
            (fixture / 'backend').mkdir(parents=True)
            (fixture / 'backend/__init__.py').write_text('')
            (fixture / 'backend/schema.py').write_text('class UnsupportedSchemaError(Exception): pass\n')
            (fixture / 'backend/server.py').write_text('class Application:\n def __init__(self, *a, **k): raise RuntimeError("private detail")\n')
            shutil.copy2(script, fixture / 'stdio_service.py')
            p = subprocess.run([sys.executable, str(fixture / 'stdio_service.py'), str(root / 'other')], input=json.dumps({'token': token})+'\n', text=True, capture_output=True, timeout=10)
            self.assertEqual(json.loads(p.stdout), {'status': 'error', 'code': 'startup_failed'})
            self.assertEqual(p.stderr, '')

    def test_schema_status_is_bounded_with_large_jobs(self):
        script = Path(__file__).resolve().parents[1] / 'stdio_service.py'
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp) / 'data'
            token = 'a' * 32
            def run(messages):
                p = subprocess.run([sys.executable, str(script), str(data)], input=''.join(json.dumps(x)+'\n' for x in messages),
                                   text=True, capture_output=True, timeout=10, check=True,
                                   env={'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'})
                return [json.loads(x) for x in p.stdout.splitlines()]
            run([{'token': token}])
            with closing(sqlite3.connect(data / 'information.sqlite')) as db, db:
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news',?,'2026','2026','2026','2026')", ('x'*20000,))
                db.executemany("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,error) VALUES (?,'item','curator',?,'failed','2026','2026','2026',?)", [(str(i), str(i), 'e'*20000) for i in range(201)])
            response = run([{'token':token},{'id':1,'token':token,'method':'GET','path':'/api/status'}])
            self.assertEqual(response[1], {'id':1, 'result':{'schemaVersion':41}})
            full = run([{'token':token},{'id':2,'token':token,'method':'GET','path':'/api/jobs'}])
            self.assertLess(len(json.dumps(full[1])), 65536)
            self.assertIsNotNone(full[1]['result']['next'])
            with closing(sqlite3.connect(data / 'information.sqlite')) as db, db:
                self.assertEqual(db.execute('SELECT count(*) FROM processing_jobs').fetchone()[0], 201)
