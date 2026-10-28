import base64
from contextlib import closing
import json
from pathlib import Path
import select
import sqlite3
import subprocess
import tempfile
import time
import unittest


class CooperativeJobsTest(unittest.TestCase):
    def test_frame_io_failures_release_snapshot_and_allow_fresh_read(self):
        import sys
        from unittest.mock import Mock
        engine = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(engine))
        from backend.server import Application
        for operation in ('seek', 'read'):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as temp:
                data = Path(temp)
                app = Application(data/'information.sqlite', data/'raw', data/'artifacts',
                                  token='a'*32, write_scope='settings')
                raw = 'retained result ' * 10000
                with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                    db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news','t','01','01','01','01')")
                    db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,result_json) VALUES ('job','item','curator','key','failed','01','01','01',?)", (raw,))
                try:
                    page = app.handle('GET', '/api/jobs', {}, {})
                    while page.get('preparing'):
                        page = app.handle('GET', '/api/jobs', {'cursor': page['next']}, {})
                    self.assertFalse(page['recordComplete'])
                    token, spool, size, following, deadline = app.snapshot
                    timer = app.snapshot_timer
                    self.assertIsNotNone(timer)
                    broken = Mock(wraps=spool)
                    getattr(broken, operation).side_effect = OSError('synthetic frame failure')
                    app.snapshot = (token, broken, size, following, deadline)
                    with self.assertRaises(OSError):
                        app.handle('GET', '/api/jobs', {'cursor': page['next']}, {})
                    self.assertTrue(spool.closed)
                    self.assertIsNone(app.snapshot)
                    self.assertIsNone(app.snapshot_timer)
                    self.assertTrue(timer.finished.is_set())
                    self.assertIsNone(app.preparation)
                    self.assertIsNone(app.preparation_timer)
                    self.assertEqual(app.handle('GET', '/api/status', {}, {})['schemaVersion'], 46)
                    page = app.handle('GET', '/api/jobs', {}, {})
                    chunks = bytearray()
                    while True:
                        chunks.extend(base64.b64decode(page['chunk']))
                        if page['recordComplete']:
                            break
                        page = app.handle('GET', '/api/jobs', {'cursor': page['next']}, {})
                    self.assertEqual(json.loads(chunks)['result_json'], raw)
                finally:
                    app.close()

    def test_broad_and_deep_records_yield_bounded_progress(self):
        engine = Path(__file__).resolve().parents[1]
        token = 'a'*32
        cases = {'broad':'[' + '0,'*6000000 + '0]',
                 'deep':'['*8000000 + '0' + ']'*8000000,
                 'scalar':'"'+'x'*16000000+'"'}
        for name, nested in cases.items():
            with self.subTest(shape=name), tempfile.TemporaryDirectory() as temp:
                data = Path(temp)/'data'
                command = [str(engine/'.prepared/python/bin/python3'), str(engine/'stdio_service.py'), str(data)]
                env = {'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
                subprocess.run(command, input=json.dumps({'token':token})+'\n', text=True,
                               capture_output=True, check=True, env=env, timeout=15)
                raw = '{"ignored":'+nested+',"stages":{"curator":{"status":"failed"}}}'
                with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                    db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news','t','01','01','01','01')")
                    db.execute("INSERT INTO curator_runs(id,item_id,status,started_at,finished_at) VALUES ('success','item','succeeded','02','03')")
                    db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at) VALUES ('older','item','curator','older','failed','01','01','01')")
                    db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,result_json) VALUES ('job','item','auto','key','failed','01','01','01',?)", (raw,))
                process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, text=True, env=env)
                def send(message):
                    started=time.monotonic()
                    process.stdin.write(json.dumps(message)+'\n'); process.stdin.flush()
                    self.assertTrue(select.select([process.stdout],[],[],4)[0], 'request exceeded four seconds')
                    reply=json.loads(process.stdout.readline())
                    self.assertLess(time.monotonic()-started,4)
                    return reply
                try:
                    self.assertEqual(send({'token':token}), {'status':'ready'})
                    page=send({'id':1,'token':token,'method':'GET','path':'/api/jobs'})['result']
                    self.assertTrue(page.get('preparing'))
                    self.assertEqual(page['chunk'],'')
                    self.assertFalse(page['recordComplete'])
                    self.assertTrue(page['next'])
                    cursor=page['next']; chunks=bytearray(); records=[]; progress=1
                    while cursor:
                        self.assertEqual(send({'id':2,'token':token,'method':'GET','path':'/api/status'})['result']['schemaVersion'],46)
                        page=send({'id':3,'token':token,'method':'GET','path':'/api/jobs','query':{'cursor':cursor}})['result']
                        if page.get('preparing'):
                            progress+=1
                            self.assertEqual(page['chunk'],''); self.assertFalse(page['recordComplete'])
                        chunks.extend(base64.b64decode(page['chunk']))
                        if page['recordComplete']:
                            records.append(json.loads(chunks)); chunks.clear()
                        cursor=page['next']
                    self.assertGreater(progress,1)
                    self.assertEqual([x['id'] for x in records],['job','older'])
                    self.assertEqual(records[0]['result_json'],raw)
                    self.assertTrue(records[0]['resolved'])
                finally:
                    process.stdin.close()
                    try: process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.terminate(); process.wait(timeout=10)
                    process.stdout.close(); process.stderr.close()

    def test_preparation_refreshes_idle_deadline_and_expiry_releases_reader(self):
        import sys
        from unittest.mock import patch
        engine = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(engine))
        from backend import server
        clock = [1000.0]
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)/'data'
            app = server.Application(data/'information.sqlite', data/'raw', data/'artifacts', token='a'*32, write_scope='settings')
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news','t','01','01','01','01')")
                raw='{"ignored":[' + '0,'*200000 + '0],"stages":{"curator":{"status":"failed"}}}'
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,result_json) VALUES ('job','item','auto','key','failed','01','01','01',?)", (raw,))
            try:
                with patch.object(server.time, 'monotonic', side_effect=lambda: clock[0]):
                    frame=app.handle('GET','/api/jobs',{}, {})
                    self.assertTrue(frame['preparing'])
                    for _ in range(3):
                        clock[0] += 119
                        frame=app.handle('GET','/api/jobs',{'cursor':frame['next']}, {})
                        self.assertTrue(frame['preparing'])
                    clock[0] += 121
                    with self.assertRaises(ValueError):
                        app.handle('GET','/api/jobs',{'cursor':frame['next']}, {})
                    self.assertEqual(app.handle('GET','/api/status',{}, {})['schemaVersion'],46)
                with closing(sqlite3.connect(data/'information.sqlite')) as db:
                    db.execute("UPDATE items SET title='changed'")
                    db.commit()
                    self.assertEqual(db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0],0)
            finally:
                app.close()

    def test_idle_timer_closes_preparation_without_another_request(self):
        import sys
        from unittest.mock import patch
        engine=Path(__file__).resolve().parents[1]
        sys.path.insert(0,str(engine))
        from backend import server
        timer=server.threading.Timer
        clock=[1000.0]
        with tempfile.TemporaryDirectory() as temp:
            data=Path(temp)/'data'
            app=server.Application(data/'information.sqlite',data/'raw',data/'artifacts',token='a'*32,write_scope='settings')
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news','t','01','01','01','01')")
                raw='{"ignored":'+'['*150000+'0'+']'*150000+',"stages":{"curator":{"status":"failed"}}}'
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,result_json) VALUES ('job','item','auto','key','failed','01','01','01',?)", (raw,))
            try:
                with patch.object(server.threading,'Timer',side_effect=lambda interval,fn,args: timer(0.05,fn,args=args)), patch.object(server.time,'monotonic',side_effect=lambda:clock[0]):
                    frame=app.handle('GET','/api/jobs',{}, {})
                    for _ in range(20):
                        self.assertTrue(frame['preparing'])
                        frame=app.handle('GET','/api/jobs',{'cursor':frame['next']}, {})
                    clock[0]+=121
                    time.sleep(0.2)
                    with closing(sqlite3.connect(data/'information.sqlite')) as db:
                        db.execute("UPDATE processing_jobs SET status='succeeded'")
                        db.commit()
                        self.assertEqual(db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0],0)
                    with self.assertRaises(ValueError):
                        app.handle('GET','/api/jobs',{'cursor':frame['next']}, {})
            finally:
                app.close()

    def test_new_enumeration_replaces_preparation_and_invalidates_old_cursor(self):
        import sys
        engine=Path(__file__).resolve().parents[1]
        sys.path.insert(0,str(engine))
        from backend import server
        with tempfile.TemporaryDirectory() as temp:
            data=Path(temp)/'data'
            app=server.Application(data/'information.sqlite',data/'raw',data/'artifacts',token='a'*32,write_scope='settings')
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,result_json) VALUES ('job','missing','curator','key','failed','01','01','01',?)", ('x'*300000,))
            try:
                old=app.handle('GET','/api/jobs',{}, {})
                with self.assertRaises(ValueError):
                    app.handle('GET','/api/jobs',{'cursor':'bogus'}, {})
                old=app.handle('GET','/api/jobs',{'cursor':old['next']}, {})
                new=app.handle('GET','/api/jobs',{}, {})
                self.assertTrue(old['preparing'] and new['preparing'])
                self.assertNotEqual(old['next'],new['next'])
                with self.assertRaises(ValueError):
                    app.handle('GET','/api/jobs',{'cursor':old['next']}, {})
                while new['next']:
                    new=app.handle('GET','/api/jobs',{'cursor':new['next']}, {})
                self.assertTrue(new['recordComplete'])
                self.assertEqual(app.handle('GET','/api/status',{}, {})['schemaVersion'],46)
            finally:
                app.close()

    def test_eof_closes_live_preparation(self):
        engine=Path(__file__).resolve().parents[1]
        token='a'*32
        with tempfile.TemporaryDirectory() as temp:
            data=Path(temp)/'data'
            command=[str(engine/'.prepared/python/bin/python3'),str(engine/'stdio_service.py'),str(data)]
            env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
            subprocess.run(command,input=json.dumps({'token':token})+'\n',text=True,capture_output=True,check=True,env=env)
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,result_json) VALUES ('job','missing','curator','key','failed','01','01','01',?)", ('x'*300000,))
            with subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env) as process:
                process.stdin.write(json.dumps({'token':token})+'\n'); process.stdin.flush()
                self.assertEqual(json.loads(process.stdout.readline()),{'status':'ready'})
                process.stdin.write(json.dumps({'id':1,'token':token,'method':'GET','path':'/api/jobs'})+'\n'); process.stdin.flush()
                page=json.loads(process.stdout.readline())['result']
                self.assertTrue(page['preparing'])
                process.stdin.write(json.dumps({'id':2,'token':'wrong','method':'GET','path':'/api/jobs','query':{'cursor':page['next']}})+'\n'); process.stdin.flush()
                self.assertEqual(json.loads(process.stdout.readline()),{'error':'unauthorized'})
                process.stdin.write(json.dumps({'id':3,'token':token,'method':'GET','path':'/api/jobs','query':{'cursor':page['next']}})+'\n'); process.stdin.flush()
                self.assertIn('result',json.loads(process.stdout.readline()))
                process.stdin.close()
                self.assertEqual(process.wait(timeout=10),0)
            with closing(sqlite3.connect(data/'information.sqlite')) as db:
                db.execute("UPDATE processing_jobs SET status='succeeded'"); db.commit()
                self.assertEqual(db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0],0)

    def test_progress_parser_and_spool_errors_release_and_allow_retry(self):
        import sys
        engine=Path(__file__).resolve().parents[1]
        token='a'*32
        code="""import sys
sys.path.insert(0,sys.argv[1])
import backend.server as server
mode=sys.argv[3]
if mode=='parser':
 original=server.aggregate_failed_stages_steps
 failed=False
 def failing(*args):
  global failed
  it=original(*args)
  try:
   for index, value in enumerate(it):
    if not failed and index==3:
     failed=True
     raise OSError('private synthetic parser error')
    yield value
  finally: it.close()
 server.aggregate_failed_stages_steps=failing
else:
 original=server.SnapshotWriter.text_column_steps
 failed=False
 def failing(self,*args):
  global failed
  it=original(self,*args)
  try:
   for index,value in enumerate(it):
    if not failed and index==3:
     failed=True
     raise OSError('private synthetic spool error')
    yield value
  finally: it.close()
 server.SnapshotWriter.text_column_steps=failing
import stdio_service
sys.argv=[sys.argv[0],sys.argv[2]]
sys.exit(stdio_service.main())
"""
        for mode in ('parser','spool'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                data=Path(temp)/'data'
                command=[sys.executable,str(engine/'stdio_service.py'),str(data)]
                subprocess.run(command,input=json.dumps({'token':token})+'\n',text=True,capture_output=True,check=True)
                raw='{"ignored":['+'0,'*200000+'0],"stages":{"curator":{"status":"failed"}}}'
                with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                    db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news','t','01','01','01','01')")
                    db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,result_json) VALUES ('job','item','auto','key','failed','01','01','01',?)", (raw,))
                process=subprocess.Popen([sys.executable,'-c',code,str(engine),str(data),mode],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                def send(value):
                    process.stdin.write(json.dumps(value)+'\n'); process.stdin.flush()
                    return json.loads(process.stdout.readline())
                try:
                    self.assertEqual(send({'token':token}),{'status':'ready'})
                    reply=send({'id':1,'token':token,'method':'GET','path':'/api/jobs'})
                    self.assertTrue(reply['result']['preparing'])
                    while 'result' in reply and reply['result'].get('preparing'):
                        reply=send({'id':1,'token':token,'method':'GET','path':'/api/jobs','query':{'cursor':reply['result']['next']}})
                    self.assertEqual(reply,{'id':1,'error':'operation failed'})
                    self.assertEqual(send({'id':2,'token':token,'method':'GET','path':'/api/status'})['result']['schemaVersion'],46)
                    page=send({'id':3,'token':token,'method':'GET','path':'/api/jobs'})['result']
                    chunks=bytearray()
                    while True:
                        chunks.extend(base64.b64decode(page['chunk']))
                        if page['recordComplete']: break
                        page=send({'id':3,'token':token,'method':'GET','path':'/api/jobs','query':{'cursor':page['next']}})['result']
                    self.assertEqual(json.loads(chunks)['result_json'],raw)
                finally:
                    process.stdin.close(); self.assertEqual(process.wait(timeout=10),0)
                    self.assertEqual(process.stderr.read(),'')
                    process.stdout.close(); process.stderr.close()
                with closing(sqlite3.connect(data/'information.sqlite')) as db:
                    self.assertEqual(db.execute('SELECT result_json FROM processing_jobs').fetchone()[0],raw)
                    self.assertEqual(db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0],0)

    def test_large_shapes_remain_bounded_for_complete_traced_read(self):
        import sys
        engine=Path(__file__).resolve().parents[1]
        shapes={'broad':'['+'0,'*6000000+'0]', 'deep':'['*8000000+'0'+']'*8000000}
        code="""import sys,tracemalloc,base64,hashlib
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from backend.server import Application
root=Path(sys.argv[2]); app=Application(root/'information.sqlite',root/'raw',root/'artifacts',token='a'*32,write_scope='settings')
tracemalloc.start(); frame=app.handle('GET','/api/jobs',{},{}); digest=hashlib.sha256(); size=0; progress=0
while True:
 chunk=base64.b64decode(frame['chunk']); digest.update(chunk); size+=len(chunk)
 progress+=bool(frame.get('preparing'))
 if frame['next'] is None: break
 frame=app.handle('GET','/api/jobs',{'cursor':frame['next']},{})
print(tracemalloc.get_traced_memory()[1],size,progress,digest.hexdigest())
app.close()
"""
        for name,nested in shapes.items():
            with self.subTest(shape=name), tempfile.TemporaryDirectory() as temp:
                data=Path(temp)/'data'
                subprocess.run([sys.executable,str(engine/'stdio_service.py'),str(data)],input=json.dumps({'token':'a'*32})+'\n',text=True,capture_output=True,check=True)
                raw='{"ignored":'+nested+',"stages":{"curator":{"status":"failed"}}}'
                with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                    db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news','t','01','01','01','01')")
                    db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,result_json) VALUES ('job','item','auto','key','failed','01','01','01',?)", (raw,))
                run=subprocess.run([sys.executable,'-c',code,str(engine),str(data)],text=True,capture_output=True,check=True,timeout=180)
                peak,size,progress,digest=run.stdout.split()
                self.assertLess(int(peak),4*1024*1024,(name,peak))
                self.assertGreater(int(size),len(raw))
                self.assertGreater(int(progress),1)
                self.assertEqual(len(digest),64)

    def test_record_frames_refresh_idle_deadline(self):
        import sys
        from unittest.mock import patch
        engine=Path(__file__).resolve().parents[1]
        sys.path.insert(0,str(engine))
        from backend import server
        clock=[1000.0]
        with tempfile.TemporaryDirectory() as temp:
            data=Path(temp)/'data'
            app=server.Application(data/'information.sqlite',data/'raw',data/'artifacts',token='a'*32,write_scope='settings')
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,error) VALUES ('job','missing','curator','key','failed','01','01','01',?)", ('x'*100000,))
            try:
                with patch.object(server.time,'monotonic',side_effect=lambda:clock[0]):
                    page=app.handle('GET','/api/jobs',{}, {})
                    self.assertFalse(page['recordComplete'])
                    for _ in range(2):
                        clock[0]+=119
                        page=app.handle('GET','/api/jobs',{'cursor':page['next']}, {})
                        self.assertFalse(page['recordComplete'])
                    clock[0]+=121
                    with self.assertRaises(ValueError):
                        app.handle('GET','/api/jobs',{'cursor':page['next']}, {})
                    self.assertEqual(app.handle('GET','/api/status',{}, {})['schemaVersion'],46)
            finally:
                app.close()

    def test_encoded_capacity_refusal_after_progress_preserves_record(self):
        import sys
        engine=Path(__file__).resolve().parents[1]
        token='a'*32
        with tempfile.TemporaryDirectory() as temp:
            data=Path(temp)/'data'
            subprocess.run([sys.executable,str(engine/'stdio_service.py'),str(data)],input=json.dumps({'token':token})+'\n',text=True,capture_output=True,check=True)
            raw='\n'*300000
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,result_json) VALUES ('job','missing','curator','key','failed','01','01','01',?)", (raw,))
            code="""import sys
sys.path.insert(0,sys.argv[1])
import backend.server as server
original=server.SnapshotWriter.__init__
def limited(self,output,limit=0): original(self,output,limit=350000)
server.SnapshotWriter.__init__=limited
import stdio_service
sys.argv=[sys.argv[0],sys.argv[2]]
sys.exit(stdio_service.main())
"""
            process=subprocess.Popen([sys.executable,'-c',code,str(engine),str(data)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            def send(value):
                process.stdin.write(json.dumps(value)+'\n'); process.stdin.flush()
                return json.loads(process.stdout.readline())
            try:
                self.assertEqual(send({'token':token}),{'status':'ready'})
                reply=send({'id':1,'token':token,'method':'GET','path':'/api/jobs'})
                self.assertTrue(reply['result']['preparing'])
                while 'result' in reply and reply['result'].get('preparing'):
                    reply=send({'id':1,'token':token,'method':'GET','path':'/api/jobs','query':{'cursor':reply['result']['next']}})
                self.assertEqual(reply,{'id':1,'error':'job record is too large','code':'job_record_too_large'})
                self.assertEqual(send({'id':2,'token':token,'method':'GET','path':'/api/status'})['result']['schemaVersion'],46)
            finally:
                process.stdin.close(); self.assertEqual(process.wait(timeout=10),0)
                self.assertEqual(process.stderr.read(),'')
                process.stdout.close(); process.stderr.close()
            with closing(sqlite3.connect(data/'information.sqlite')) as db:
                self.assertEqual(db.execute('SELECT result_json FROM processing_jobs').fetchone()[0],raw)

    def test_read_snapshot_handles_special_characters_in_owned_path(self):
        engine=Path(__file__).resolve().parents[1]
        token='a'*32
        with tempfile.TemporaryDirectory() as temp:
            data=Path(temp)/'data #? name'
            command=[str(engine/'.prepared/python/bin/python3'),str(engine/'stdio_service.py'),str(data)]
            env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
            subprocess.run(command,input=json.dumps({'token':token})+'\n',text=True,capture_output=True,check=True,env=env)
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at) VALUES ('job','missing','curator','key','failed','01','01','01')")
            requests=[{'token':token},{'id':1,'token':token,'method':'GET','path':'/api/jobs'}]
            run=subprocess.run(command,input=''.join(json.dumps(x)+'\n' for x in requests),text=True,capture_output=True,check=True,env=env)
            reply=json.loads(run.stdout.splitlines()[1])['result']
            self.assertEqual(json.loads(base64.b64decode(reply['chunk']))['id'],'job')
