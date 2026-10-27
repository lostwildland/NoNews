import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


class InitializationProbeTest(unittest.TestCase):
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
            with sqlite3.connect(database) as db:
                self.assertEqual(db.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0], 0)
            subprocess.run([sys.executable, '-c', 'import sys; sys.path.insert(0,sys.argv[1]); from backend.core import InformationDB; InformationDB(sys.argv[2]).close()', str(root), str(database)], check=True)
            with sqlite3.connect(database) as db:
                self.assertEqual(db.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone(), ('41',))


    def test_concurrent_empty_initialization_and_unknown_history(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / 'db'
            sqlite3.connect(database).close()
            code = 'import sys; sys.path.insert(0,sys.argv[1]); from backend.core import InformationDB; InformationDB(sys.argv[2]).close()'
            processes = [subprocess.Popen([sys.executable, '-c', code, str(root), str(database)], stderr=subprocess.PIPE) for _ in range(2)]
            for process in processes:
                _, error = process.communicate(timeout=20)
                self.assertEqual(process.returncode, 0, error)
            unknown = Path(temp) / 'unknown'
            with sqlite3.connect(unknown) as db:
                db.execute('CREATE TABLE history(value TEXT)')
                db.execute("INSERT INTO history VALUES ('keep')")
            before = unknown.read_bytes()
            rejected = subprocess.run([sys.executable, '-c', code, str(root), str(unknown)], capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertEqual(unknown.read_bytes(), before)

    def test_probe_rolls_back_existing_and_absent_settings_and_rejects_write(self):
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
            with sqlite3.connect(database) as db:
                self.assertEqual(db.execute('SELECT * FROM app_settings').fetchall(), [])
                db.execute("INSERT INTO app_settings VALUES ('processors','3','original')")
                db.execute("INSERT INTO app_settings VALUES ('other','keep','timestamp')")
            self.assertEqual(json.loads(start().stdout), {'status':'ready'})
            with sqlite3.connect(database) as db:
                self.assertEqual(db.execute('SELECT * FROM app_settings ORDER BY key').fetchall(), [('other','keep','timestamp'),('processors','3','original')])
                db.execute("CREATE TRIGGER reject_setting BEFORE UPDATE ON app_settings BEGIN SELECT RAISE(ABORT,'private'); END")
            result = start()
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(json.loads(result.stdout), {'status':'error','code':'data_unavailable'})
            with sqlite3.connect(database) as db:
                self.assertEqual(db.execute('SELECT * FROM app_settings ORDER BY key').fetchall(), [('other','keep','timestamp'),('processors','3','original')])
