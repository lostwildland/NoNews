import json
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest


class InitializationProbeTest(unittest.TestCase):
    def test_initialization_waits_for_a_reader_during_wal_conversion(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / 'db'
            with closing(sqlite3.connect(database)) as blocker:
                blocker.execute('BEGIN')
                blocker.execute('SELECT count(*) FROM sqlite_master').fetchone()
                code = 'import sys; sys.path.insert(0,sys.argv[1]); from backend.core import InformationDB; print("opening",flush=True); InformationDB(sys.argv[2]).close()'
                with subprocess.Popen([sys.executable, '-c', code, str(root), str(database)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
                    self.assertEqual(process.stdout.readline().strip(), 'opening')
                    time.sleep(0.15)
                    blocker.rollback()
                    _, error = process.communicate(timeout=20)
                    self.assertEqual(process.returncode, 0, error)

    def test_interrupted_initialization_retries_without_partial_schema(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / 'db'
            code = '''import sys,sqlite3
sys.path.insert(0,sys.argv[1])
from backend import schema, core
original=core.ensure_schema
def interrupted(db):
 original(db)
 import os; os._exit(73)
core.ensure_schema=interrupted
connection=sqlite3.connect(sys.argv[2],isolation_level=None)
try: schema.ensure(connection)
except RuntimeError: pass
print(connection.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0])
connection.close()
'''
            p = subprocess.run([sys.executable, '-c', code, str(root), str(database)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 73)
            with closing(sqlite3.connect(database)) as db, db:
                self.assertEqual(db.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0], 0)
            subprocess.run([sys.executable, '-c', 'import sys; sys.path.insert(0,sys.argv[1]); from backend.core import InformationDB; InformationDB(sys.argv[2]).close()', str(root), str(database)], check=True)
            with closing(sqlite3.connect(database)) as db, db:
                self.assertEqual(db.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone(), ('41',))


    def test_concurrent_empty_initialization_and_unknown_history(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / 'db'
            sqlite3.connect(database).close()
            code = 'import sys; sys.path.insert(0,sys.argv[1]); from backend.core import InformationDB; InformationDB(sys.argv[2]).close()'
            for attempt in range(8):
                candidate = Path(temp) / ('concurrent-' + str(attempt))
                sqlite3.connect(candidate).close()
                synchronized = code.replace('from backend.core import InformationDB;', 'from backend.core import InformationDB; print("opening",flush=True); sys.stdin.readline();')
                processes = [subprocess.Popen([sys.executable, '-c', synchronized, str(root), str(candidate)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
                try:
                    for process in processes:
                        self.assertEqual(process.stdout.readline().strip(), 'opening')
                    for process in processes:
                        process.stdin.write('start\n'); process.stdin.flush()
                    results = [(process, process.communicate(timeout=20)[1]) for process in processes]
                    for process, error in results:
                        self.assertEqual(process.returncode, 0, error)
                finally:
                    for process in processes:
                        if process.poll() is None:
                            process.kill()
                        process.communicate()
            unknown = Path(temp) / 'unknown'
            with closing(sqlite3.connect(unknown)) as db, db:
                db.execute('CREATE TABLE history(value TEXT)')
                db.execute("INSERT INTO history VALUES ('keep')")
            before = unknown.read_bytes()
            rejected = subprocess.run([sys.executable, '-c', code, str(root), str(unknown)], capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertEqual(unknown.read_bytes(), before)

    def test_probe_rolls_back_settings_and_refuses_unverified_write_blocker(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp) / 'data'
            script = root / 'stdio_service.py'
            token = 'a' * 32
            command = [sys.executable, str(script), str(data)]
            def start():
                return subprocess.run(command, input=json.dumps({'token': token})+'\n', capture_output=True, text=True, timeout=10)
            self.assertEqual(json.loads(start().stdout), {'status':'ready'})
            database = data / 'information.sqlite'
            with closing(sqlite3.connect(database)) as db, db:
                self.assertEqual(db.execute('SELECT * FROM app_settings').fetchall(), [])
                db.execute("INSERT INTO app_settings VALUES ('processors','3','original')")
                db.execute("INSERT INTO app_settings VALUES ('other','keep','timestamp')")
            self.assertEqual(json.loads(start().stdout), {'status':'ready'})
            with closing(sqlite3.connect(database)) as db, db:
                self.assertEqual(db.execute('SELECT * FROM app_settings ORDER BY key').fetchall(), [('other','keep','timestamp'),('processors','3','original')])
                db.execute("CREATE TRIGGER reject_setting BEFORE UPDATE ON app_settings BEGIN SELECT RAISE(ABORT,'private'); END")
            result = start()
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(json.loads(result.stdout), {'status':'error','code':'schema_migration_required'})
            with closing(sqlite3.connect(database)) as db, db:
                self.assertEqual(db.execute('SELECT * FROM app_settings ORDER BY key').fetchall(), [('other','keep','timestamp'),('processors','3','original')])
