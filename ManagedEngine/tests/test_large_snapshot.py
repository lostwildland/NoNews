from contextlib import closing
import base64
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


class LargeSnapshotTest(unittest.TestCase):
    def test_large_full_read_has_bounded_python_allocations(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp) / 'data'
            subprocess.run([sys.executable, str(root / 'stdio_service.py'), str(data)],
                           input=json.dumps({'token':'a'*32})+'\n', text=True, capture_output=True, check=True)
            with closing(sqlite3.connect(data / 'information.sqlite')) as db, db:
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,result_json) VALUES ('job','missing','curator','key','succeeded','now','now','now',?)", ('x' * (16 * 1024 * 1024),))
            code = """import sys,tracemalloc
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from backend.server import Application
root=Path(sys.argv[2]); app=Application(root/'information.sqlite',root/'raw',root/'artifacts',token='a'*32,write_scope='settings')
tracemalloc.start()
frame=app.handle('GET','/api/jobs',{}, {})
while frame['next']: frame=app.handle('GET','/api/jobs',{'cursor':frame['next']}, {})
print(tracemalloc.get_traced_memory()[1])
app._clear_snapshot()
"""
            result = subprocess.run([sys.executable, '-c', code, str(root), str(data)],
                                    text=True, capture_output=True, check=True, timeout=30)
            self.assertLess(int(result.stdout), 4 * 1024 * 1024, result.stdout)

    def test_large_error_and_auto_result_are_bounded(self):
        root = Path(__file__).resolve().parents[1]
        for kind in ('error', 'auto'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                data = Path(temp) / 'data'
                subprocess.run([sys.executable, str(root / 'stdio_service.py'), str(data)],
                               input=json.dumps({'token':'a'*32})+'\n', text=True, capture_output=True, check=True)
                large = 'x' * (16 * 1024 * 1024)
                with closing(sqlite3.connect(data / 'information.sqlite')) as db, db:
                    db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news','title','now','now','now','now')")
                    db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,error,result_json) VALUES ('job','item',?,'key','failed','now','now','now',?,?)",
                               ('auto' if kind == 'auto' else 'curator', large if kind == 'error' else None,
                                json.dumps({'padding':large, 'stages':{'curator':{'status':'failed'}}}) if kind == 'auto' else None))
                code = """import sys,tracemalloc
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from backend.server import Application
root=Path(sys.argv[2]); app=Application(root/'information.sqlite',root/'raw',root/'artifacts',token='a'*32,write_scope='settings')
tracemalloc.start(); frame=app.handle('GET','/api/jobs',{}, {})
while frame['next']: frame=app.handle('GET','/api/jobs',{'cursor':frame['next']}, {})
print(tracemalloc.get_traced_memory()[1]); app._clear_snapshot()
"""
                result = subprocess.run([sys.executable, '-c', code, str(root), str(data)],
                                        text=True, capture_output=True, check=True, timeout=30)
                self.assertLess(int(result.stdout), 4 * 1024 * 1024, result.stdout)

    def test_large_auto_identity_and_timestamp_have_bounded_allocations(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)/'data'
            subprocess.run([sys.executable, str(root/'stdio_service.py'), str(data)],
                           input=json.dumps({'token':'a'*32})+'\n', text=True, capture_output=True, check=True)
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                item = 'i'*(16*1024*1024)
                stamp = 't'*(1024*1024)
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES (?,'news','title','now','now','now','now')", (item,))
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,result_json) VALUES ('job',?,'auto','key','failed','now','now',?,?)", (item, stamp, json.dumps({'stages':{'curator':{'status':'failed'}}})))
                db.execute("INSERT INTO curator_runs(id,item_id,status,started_at,finished_at) VALUES ('success',?,'succeeded','now',?)", (item, stamp+'z'))
            code = """import sys,tracemalloc
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from backend.server import Application
root=Path(sys.argv[2]); app=Application(root/'information.sqlite',root/'raw',root/'artifacts',token='a'*32,write_scope='settings')
tracemalloc.start(); frame=app.handle('GET','/api/jobs',{}, {})
while frame['next']: frame=app.handle('GET','/api/jobs',{'cursor':frame['next']}, {})
print(tracemalloc.get_traced_memory()[1]); app._clear_snapshot()
"""
            result = subprocess.run([sys.executable,'-c',code,str(root),str(data)], text=True,
                                    capture_output=True,check=True,timeout=30)
            self.assertLess(int(result.stdout), 4*1024*1024, result.stdout)

    def test_large_title_and_stage_error_have_bounded_allocations(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp) / 'data'
            subprocess.run([sys.executable, str(root/'stdio_service.py'), str(data)],
                           input=json.dumps({'token':'a'*32})+'\n', text=True, capture_output=True, check=True)
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                large = 'x'*(16*1024*1024)
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news',?,'now','now','now','now')", (large,))
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at) VALUES ('job','item','curator','key','failed','now','now','now')")
                db.execute("INSERT INTO stage_state(item_id,stage,status,error,updated_at) VALUES ('item','curator','failed',?,'now')", (large,))
            code = """import sys,tracemalloc
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from backend.server import Application
root=Path(sys.argv[2]); app=Application(root/'information.sqlite',root/'raw',root/'artifacts',token='a'*32,write_scope='settings')
tracemalloc.start(); frame=app.handle('GET','/api/jobs',{}, {})
while frame['next']: frame=app.handle('GET','/api/jobs',{'cursor':frame['next']}, {})
print(tracemalloc.get_traced_memory()[1]); app._clear_snapshot()
"""
            result = subprocess.run([sys.executable, '-c', code, str(root), str(data)],
                                    text=True, capture_output=True, check=True, timeout=30)
            self.assertLess(int(result.stdout), 4*1024*1024, result.stdout)

    def test_large_item_identifier_has_bounded_allocations(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)/'data'
            subprocess.run([sys.executable, str(root/'stdio_service.py'), str(data)],
                           input=json.dumps({'token':'a'*32})+'\n', text=True, capture_output=True, check=True)
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                big = 'i'*(16*1024*1024)
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES (?,'news','title','now','now','now','now')", (big,))
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at) VALUES ('job',?,'curator','key','failed','now','now','now')", (big,))
            code = """import sys,tracemalloc
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from backend.server import Application
root=Path(sys.argv[2]); app=Application(root/'information.sqlite',root/'raw',root/'artifacts',token='a'*32,write_scope='settings')
tracemalloc.start(); frame=app.handle('GET','/api/jobs',{}, {})
while frame['next']: frame=app.handle('GET','/api/jobs',{'cursor':frame['next']}, {})
print(tracemalloc.get_traced_memory()[1]); app._clear_snapshot()
"""
            result = subprocess.run([sys.executable, '-c', code, str(root), str(data)],
                                    text=True, capture_output=True, check=True, timeout=30)
            self.assertLess(int(result.stdout), 4*1024*1024, result.stdout)

    def test_capacity_refusal_keeps_service_and_rows(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp) / 'data'
            subprocess.run([sys.executable, str(root/'stdio_service.py'), str(data)],
                           input=json.dumps({'token':'a'*32})+'\n', text=True, capture_output=True, check=True)
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,error) VALUES ('job','missing','curator','key','failed','now','now','now',?)", ('x'*1000,))
            code = """import sys
sys.path.insert(0,sys.argv[1])
import backend.server
backend.server.SNAPSHOT_CAPACITY=128
import stdio_service
sys.argv=[sys.argv[0],sys.argv[2]]
sys.exit(stdio_service.main())
"""
            token = 'a'*32
            messages = [{'token':token}, {'id':1,'token':token,'method':'GET','path':'/api/jobs'},
                        {'id':2,'token':token,'method':'GET','path':'/api/status'}]
            run = subprocess.run([sys.executable, '-c', code, str(root), str(data)],
                                 input=''.join(json.dumps(x)+'\n' for x in messages),
                                 text=True, capture_output=True, check=True, timeout=15)
            replies = [json.loads(x) for x in run.stdout.splitlines()]
            self.assertEqual(replies[1], {'id':1,'error':'job record is too large','code':'job_record_too_large'})
            self.assertEqual(replies[2]['result']['schemaVersion'], 41)
            with closing(sqlite3.connect(data/'information.sqlite')) as db:
                self.assertEqual(db.execute('SELECT error FROM processing_jobs').fetchone()[0], 'x'*1000)

    def test_auto_capacity_refusal_keeps_service_and_rows(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)/'data'
            subprocess.run([sys.executable,str(root/'stdio_service.py'),str(data)],
                           input=json.dumps({'token':'a'*32})+'\n',text=True,capture_output=True,check=True)
            stored = json.dumps({'stages':{'curator':{'status':'failed'}},'ignored':'x'*1000})
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news','title','now','now','now','now')")
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,result_json) VALUES ('job','item','auto','key','failed','now','now','now',?)", (stored,))
            code = """import sys
sys.path.insert(0,sys.argv[1])
import backend.server
backend.server.SNAPSHOT_CAPACITY=128
import stdio_service
sys.argv=[sys.argv[0],sys.argv[2]]
sys.exit(stdio_service.main())
"""
            token='a'*32
            requests=[{'token':token},{'id':1,'token':token,'method':'GET','path':'/api/jobs'},
                      {'id':2,'token':token,'method':'GET','path':'/api/status'}]
            run=subprocess.run([sys.executable,'-c',code,str(root),str(data)],
                               input=''.join(json.dumps(x)+'\n' for x in requests),
                               text=True,capture_output=True,check=True,timeout=15)
            replies=[json.loads(x) for x in run.stdout.splitlines()]
            self.assertEqual(replies[1], {'id':1,'error':'job record is too large','code':'job_record_too_large'})
            self.assertEqual(replies[2]['result']['schemaVersion'], 41)
            with closing(sqlite3.connect(data/'information.sqlite')) as db:
                self.assertEqual(db.execute('SELECT result_json FROM processing_jobs').fetchone()[0], stored)

    def test_stack_spill_failures_do_not_stop_service(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            data=Path(temp)/'data'
            subprocess.run([sys.executable,str(root/'stdio_service.py'),str(data)],
                           input=json.dumps({'token':'a'*32})+'\n',text=True,capture_output=True,check=True)
            stored='{"ignored":'+'['*70000+'0'+']'*70000+',"stages":{"curator":{"status":"failed"}}}'
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news','t','01','01','01','01')")
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,result_json) VALUES ('job','item','auto','key','failed','01','01','01',?)", (stored,))
            code="""import sys
sys.path.insert(0,sys.argv[1])
import backend.job_stream as stream
mode=sys.argv[3]
original=stream.tempfile.SpooledTemporaryFile
count=0
class Broken:
 def __init__(self,*a,**k): self.file=original(*a,**k)
 def __enter__(self): return self
 def __exit__(self,*a): self.file.close()
 def seek(self,*a): return self.file.seek(*a)
 def write(self,*a):
  if mode=='write': raise OSError('synthetic private diagnostic')
  return self.file.write(*a)
 def read(self,*a): return b'' if mode=='read' else self.file.read(*a)
def factory(*a,**k):
 global count
 count+=1
 return Broken(*a,**k) if count==1 else original(*a,**k)
stream.tempfile.SpooledTemporaryFile=factory
import stdio_service
sys.argv=[sys.argv[0],sys.argv[2]]
sys.exit(stdio_service.main())
"""
            token='a'*32
            requests=[{'token':token},{'id':1,'token':token,'method':'GET','path':'/api/jobs'},
                      {'id':2,'token':token,'method':'GET','path':'/api/status'},
                      {'id':3,'token':token,'method':'GET','path':'/api/jobs'}]
            for mode in ('write', 'read'):
                with self.subTest(mode=mode):
                    run=subprocess.run([sys.executable,'-c',code,str(root),str(data),mode],
                                       input=''.join(json.dumps(x)+'\n' for x in requests),
                                       text=True,capture_output=True,check=True,timeout=15)
                    replies=[json.loads(x) for x in run.stdout.splitlines()]
                    self.assertEqual(replies[1], {'id':1,'error':'operation failed'})
                    self.assertEqual(replies[2]['result']['schemaVersion'], 41)
                    self.assertIn('result', replies[3])
                    self.assertEqual(run.stderr, '')
            with closing(sqlite3.connect(data/'information.sqlite')) as db:
                self.assertEqual(db.execute('SELECT result_json FROM processing_jobs').fetchone()[0], stored)

    def test_spool_write_failure_does_not_stop_service(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)/'data'
            subprocess.run([sys.executable, str(root/'stdio_service.py'), str(data)],
                           input=json.dumps({'token':'a'*32})+'\n', text=True, capture_output=True, check=True)
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,error) VALUES ('job','missing','curator','key','failed','now','now','now','error')")
            code = """import sys
sys.path.insert(0,sys.argv[1])
import backend.server
original=backend.server.SnapshotWriter.text_column_steps
count=0
def failing(self,*args):
 global count
 count += 1
 if count == 1: raise OSError('synthetic private diagnostic')
 yield from original(self,*args)
backend.server.SnapshotWriter.text_column_steps=failing
import stdio_service
sys.argv=[sys.argv[0],sys.argv[2]]
sys.exit(stdio_service.main())
"""
            token='a'*32
            messages=[{'token':token}, {'id':1,'token':token,'method':'GET','path':'/api/jobs'},
                      {'id':2,'token':token,'method':'GET','path':'/api/status'},
                      {'id':3,'token':token,'method':'GET','path':'/api/jobs'}]
            result=subprocess.run([sys.executable,'-c',code,str(root),str(data)],
                                  input=''.join(json.dumps(x)+'\n' for x in messages),
                                  text=True,capture_output=True,check=True,timeout=15)
            replies=[json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(replies[1], {'id':1,'error':'operation failed'})
            self.assertEqual(replies[2]['result']['schemaVersion'], 41)
            self.assertEqual(json.loads(base64.b64decode(replies[3]['result']['chunk']))['error'], 'error')
            self.assertEqual(result.stderr, '')

    def test_large_record_public_frames_preserve_snapshot_and_refresh(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp) / 'data'
            script = root / 'stdio_service.py'
            token = 'a' * 32
            command = [sys.executable, str(script), str(data)]
            subprocess.run(command, input=json.dumps({'token': token})+'\n', text=True,
                           capture_output=True, check=True, timeout=15)
            original = ('x' * 16383 + '😀"\\\n中') * 520
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news','old','now','now','now','now')")
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,result_json) VALUES ('job','item','curator','key','succeeded','now','now','now',?)", (original,))
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True)
            def send(message):
                process.stdin.write(json.dumps(message) + '\n')
                process.stdin.flush()
                return json.loads(process.stdout.readline())
            def record(first):
                chunks = bytearray(base64.b64decode(first['chunk']))
                frame = first
                while not frame['recordComplete']:
                    response = send({'id':1, 'token':token, 'method':'GET', 'path':'/api/jobs',
                                     'query':{'cursor':frame['next']}})
                    frame = response['result']
                    chunks.extend(base64.b64decode(frame['chunk']))
                return json.loads(chunks)
            try:
                self.assertEqual(send({'token': token}), {'status':'ready'})
                first = send({'id':1, 'token':token, 'method':'GET', 'path':'/api/jobs'})['result']
                with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                    db.execute("UPDATE items SET title='new'")
                    db.execute("UPDATE processing_jobs SET result_json='new result'")
                old = record(first)
                self.assertEqual((old['title'], old['result_json']), ('old', original))
                refreshed = record(send({'id':2, 'token':token, 'method':'GET', 'path':'/api/jobs'})['result'])
                self.assertEqual((refreshed['title'], refreshed['result_json']), ('new', 'new result'))
            finally:
                process.stdin.close()
                self.assertEqual(process.wait(timeout=15), 0)
                process.stdout.close()
                process.stderr.close()

    def test_incomplete_snapshot_expires(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp) / 'data'
            subprocess.run([sys.executable, str(root / 'stdio_service.py'), str(data)],
                           input=json.dumps({'token':'a'*32})+'\n', text=True, capture_output=True, check=True)
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,result_json) VALUES ('job','missing','curator','key','succeeded','now','now','now',?)", ('x'*50000,))
            code = '''import sys,time
sys.path.insert(0,sys.argv[1])
import backend.server as server
from pathlib import Path
original=server.threading.Timer
clock=server.time.monotonic
offset=0
server.time.monotonic=lambda: clock()+offset
server.threading.Timer=lambda interval,fn,args: original(0.05,fn,args=args)
root=Path(sys.argv[2]); app=server.Application(root/'information.sqlite',root/'raw',root/'artifacts',token='a'*32,write_scope='settings')
frame=app.handle('GET','/api/jobs',{},{}); offset=121; time.sleep(0.2)
try: app.handle('GET','/api/jobs',{'cursor':frame['next']},{})
except ValueError: print('expired')
'''
            expired = subprocess.run([sys.executable, '-c', code, str(root), str(data)], capture_output=True,
                                     text=True, check=True, timeout=10)
            self.assertEqual(expired.stdout.strip(), 'expired')
