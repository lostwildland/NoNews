from contextlib import closing
import base64
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest


class JobsPagingTest(unittest.TestCase):
    def test_missing_items_do_not_hide_or_block_job_history(self):
        engine = Path(__file__).resolve().parents[1]
        for orphan_only in (False, True):
            with self.subTest(orphan_only=orphan_only), tempfile.TemporaryDirectory() as tmp:
                data = Path(tmp) / 'data'
                command = [str(engine / '.prepared/python/bin/python3'), str(engine / 'stdio_service.py'), str(data)]
                token = 'a' * 32
                env = {'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
                subprocess.run(command, input=json.dumps({'token':token})+'\n', text=True,
                               capture_output=True, check=True, env=env, timeout=10)
                values = [(1, 'older', 'item'), (2, 'orphan', 'missing'), (3, 'newer', 'item')]
                if orphan_only:
                    values = [values[1]]
                original_result = json.dumps({'retained': 'Missing item result 😀' * 3000}, ensure_ascii=False)
                original_error = 'Processing stage failed: original detail'
                with closing(sqlite3.connect(data / 'information.sqlite')) as db, db:
                    db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news','Synthetic','now','now','now','now')")
                    db.executemany("INSERT INTO processing_jobs(rowid,id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,error,result_json) VALUES (?,?,?,'curator',?,'failed','now','now','now',?,?)",
                                   [(rowid, name, item, name, original_error, original_result) for rowid, name, item in values])
                    for item in ('item', 'missing'):
                        db.executemany("INSERT INTO stage_state(item_id,stage,status,error,updated_at) VALUES (?,?,'failed',?,?)",
                                       [(item, 'curator', 'Current curator detail', '2026-10-28T01:00:00+00:00'),
                                        (item, 'editor', 'Unrelated newer stage error', '2026-10-28T02:00:00+00:00')])
                process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
                def send(message):
                    process.stdin.write(json.dumps(message)+'\n'); process.stdin.flush()
                    return json.loads(process.stdout.readline())
                try:
                    self.assertEqual(send({'token':token}), {'status':'ready'})
                    cursor, chunks, records = None, bytearray(), []
                    while True:
                        reply = send({'id':1,'token':token,'method':'GET','path':'/api/jobs',
                                      'query':{} if cursor is None else {'cursor':cursor}})
                        self.assertIn('result', reply, reply)
                        page = reply['result']
                        chunks.extend(base64.b64decode(page['chunk']))
                        if page['recordComplete']:
                            records.append(json.loads(chunks)); chunks.clear()
                        cursor = page['next']
                        if cursor is None:
                            break
                    self.assertEqual([record['id'] for record in records],
                                     ['orphan'] if orphan_only else ['newer', 'orphan', 'older'])
                    missing = next(record for record in records if record['id'] == 'orphan')
                    self.assertEqual(missing['item_id'], 'missing')
                    self.assertIsNone(missing['title'])
                    self.assertTrue(missing['itemUnavailable'])
                    self.assertFalse(missing['retryable'])
                    self.assertIn('unavailable', missing['retryBlocked'])
                    self.assertTrue(all(record['error'] == original_error and
                                        record['result_json'] == original_result for record in records))
                    self.assertTrue(all(record['stage_error'] == 'Current curator detail' for record in records))
                    self.assertTrue(all(not record['itemUnavailable'] for record in records if record['id'] != 'orphan'))
                finally:
                    process.stdin.close()
                    self.assertEqual(process.wait(timeout=10), 0)
                    process.stdout.close()
                with closing(sqlite3.connect(data / 'information.sqlite')) as db:
                    self.assertEqual(db.execute('SELECT rowid,id,item_id FROM processing_jobs ORDER BY rowid').fetchall(), values)

    def test_large_projected_text_and_recorded_error_are_preserved(self):
        engine = Path(__file__).resolve().parents[1]
        token = 'a' * 32
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'data'
            command = [str(engine / '.prepared/python/bin/python3'), str(engine / 'stdio_service.py'), str(data)]
            env = {'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
            subprocess.run(command, input=json.dumps({'token':token})+'\n', text=True,
                           capture_output=True, check=True, env=env, timeout=10)
            error = 'papererror: ' + ('x' * 70000) + ' HTTP 403 😀"\\'
            title = ('长😀"\\\n' * 30000)
            stage_error = ('stage detail 😀"\\' * 25000)
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news',?,'now','now','now','now')", (title,))
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,error,result_json) VALUES ('job','item','curator','key','failed','now','now','now',?,NULL)", (error,))
                db.execute("INSERT INTO stage_state(item_id,stage,status,error,updated_at) VALUES ('item','curator','failed',?,'now')", (stage_error,))
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            def send(value):
                process.stdin.write(json.dumps(value)+'\n'); process.stdin.flush()
                return json.loads(process.stdout.readline())
            try:
                self.assertEqual(send({'token':token}), {'status':'ready'})
                cursor, chunks = None, bytearray()
                while True:
                    page = send({'id':1,'token':token,'method':'GET','path':'/api/jobs',
                                 'query':{} if cursor is None else {'cursor':cursor}})['result']
                    chunks.extend(base64.b64decode(page['chunk']))
                    cursor = page['next']
                    if page['recordComplete']:
                        break
                result = json.loads(chunks)
                self.assertEqual((result['error'], result['title'], result['stage_error'], result['result_json']),
                                 (error, title, stage_error, None))
                self.assertEqual(result['cause'], 'source_browser')
                self.assertEqual(send({'id':2,'token':token,'method':'GET','path':'/api/status'})['result']['schemaVersion'], 41)
            finally:
                process.stdin.close(); self.assertEqual(process.wait(timeout=10), 0)
                process.stdout.close(); process.stderr.close()
            with closing(sqlite3.connect(data/'information.sqlite')) as db:
                self.assertEqual(db.execute("SELECT error,result_json FROM processing_jobs WHERE id='job'").fetchone(), (error, None))
                self.assertEqual(db.execute("SELECT error FROM stage_state WHERE item_id='item'").fetchone(), (stage_error,))

    def test_large_job_identifiers_and_other_text_fields_are_complete(self):
        engine = Path(__file__).resolve().parents[1]
        token = 'a'*32
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)/'data'
            command = [str(engine/'.prepared/python/bin/python3'), str(engine/'stdio_service.py'), str(data)]
            env = {'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
            subprocess.run(command, input=json.dumps({'token':token})+'\n', text=True, capture_output=True, check=True, env=env)
            large = ('长😀"\\' * 20000)
            item = 'item' + large
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES (?,'news','title','now','now','now','now')", (item,))
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,batch_id) VALUES (?,?,?,'key','failed',?,?,?,?)", ('job'+large,item,'stage'+large,large,large,large,large))
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            def send(value):
                process.stdin.write(json.dumps(value)+'\n'); process.stdin.flush()
                return json.loads(process.stdout.readline())
            try:
                self.assertEqual(send({'token':token}), {'status':'ready'})
                cursor, chunks = None, bytearray()
                while True:
                    page = send({'id':1,'token':token,'method':'GET','path':'/api/jobs','query':{} if cursor is None else {'cursor':cursor}})['result']
                    chunks.extend(base64.b64decode(page['chunk']))
                    if page['recordComplete']: break
                    cursor = page['next']
                result = json.loads(chunks)
                self.assertEqual((result['id'],result['item_id'],result['stage']), ('job'+large,item,'stage'+large))
                for name in ('available_at','created_at','updated_at','batch_id'):
                    self.assertEqual(result[name], large)
                self.assertFalse(result['resolved'])
                self.assertIn('guarded runner', result['retryBlocked'])
            finally:
                process.stdin.close(); self.assertEqual(process.wait(timeout=10), 0)
                process.stdout.close(); process.stderr.close()

    def test_stage_resolution_and_retry_meaning_survive_streaming(self):
        engine = Path(__file__).resolve().parents[1]
        token = 'a'*32
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)/'data'
            command = [str(engine/'.prepared/python/bin/python3'), str(engine/'stdio_service.py'), str(data)]
            env = {'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
            subprocess.run(command, input=json.dumps({'token':token})+'\n', text=True, capture_output=True, check=True, env=env)
            stages = ('scoring','acquisition','curator','editor','maintenance','tags','media','historical_curator')
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news','t','01','01','01','01')")
                db.executemany("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at) VALUES (?,'item',?,?,'failed','01','01','01')", [(stage,stage,stage) for stage in stages])
                db.executemany("INSERT INTO pipeline_stage_runs(job_id,item_id,stage,status,updated_at) VALUES (?,'item',?,'ready','03')", [(s,s) for s in ('scoring','acquisition','maintenance')])
                db.execute("INSERT INTO stage_state(item_id,stage,status,updated_at) VALUES ('item','acquisition','failed','01')")
                db.execute("INSERT INTO curator_runs(id,item_id,status,score,started_at,finished_at) VALUES ('curator-success','item','succeeded',5,'02','03')")
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at) VALUES ('historical-success','item','historical_curator','historical-success','succeeded','01','01','03')")
                db.execute("INSERT INTO pipeline_stage_runs(job_id,item_id,stage,status,result_json,updated_at) VALUES ('historical-success','item','curator','ready',?, '03')", (json.dumps({'run_id':'curator-success'}),))
                db.execute("INSERT INTO editor_drafts(id,item_id,created_at) VALUES ('draft','item','03')")
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            def send(value):
                process.stdin.write(json.dumps(value)+'\n'); process.stdin.flush()
                return json.loads(process.stdout.readline())
            try:
                self.assertEqual(send({'token':token}), {'status':'ready'})
                records = {}; cursor = None
                while True:
                    page = send({'id':1,'token':token,'method':'GET','path':'/api/jobs', 'query':{} if cursor is None else {'cursor':cursor}})['result']
                    self.assertTrue(page['recordComplete'])
                    record = json.loads(base64.b64decode(page['chunk']))
                    if record['status'] == 'failed':
                        records[record['stage']] = record
                    cursor = page['next']
                    if cursor is None: break
                self.assertEqual({k:v['resolved'] for k,v in records.items()},
                                 {'scoring':True,'acquisition':False,'curator':True,'editor':True,'maintenance':True,'tags':False,'media':False,'historical_curator':True})
                self.assertIn('Settings-write', records['acquisition']['retryBlocked'])
                self.assertIsNone(records['historical_curator']['retryBlocked'])
            finally:
                process.stdin.close(); self.assertEqual(process.wait(timeout=10), 0)
                process.stdout.close(); process.stderr.close()

    def test_small_auto_job_preserves_stage_resolution(self):
        engine = Path(__file__).resolve().parents[1]
        token = 'a'*32
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)/'data'
            command = [str(engine/'.prepared/python/bin/python3'), str(engine/'stdio_service.py'), str(data)]
            env = {'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
            subprocess.run(command, input=json.dumps({'token':token})+'\n', text=True, capture_output=True, check=True, env=env)
            result = json.dumps({'stages':{'curator':{'status':'failed'}}})
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news','t','01','01','01','01')")
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,result_json) VALUES ('job','item','auto','key','failed','01','01','01',?)", (result,))
                db.execute("INSERT INTO curator_runs(id,item_id,status,started_at,finished_at) VALUES ('success','item','succeeded','02','03')")
            messages = [{'token':token},{'id':1,'token':token,'method':'GET','path':'/api/jobs'}]
            response = subprocess.run(command, input=''.join(json.dumps(x)+'\n' for x in messages),
                                      text=True, capture_output=True, check=True, env=env)
            page = json.loads(response.stdout.splitlines()[1])['result']
            record = json.loads(base64.b64decode(page['chunk']))
            self.assertTrue(record['resolved'])
            self.assertFalse(record['retryable'])
            self.assertEqual(record['result_json'], result)
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                db.execute("INSERT INTO stage_state(item_id,stage,status,updated_at) VALUES ('item','curator','failed','01')")
            response = subprocess.run(command, input=''.join(json.dumps(x)+'\n' for x in messages),
                                      text=True, capture_output=True, check=True, env=env)
            blocked = json.loads(base64.b64decode(json.loads(response.stdout.splitlines()[1])['result']['chunk']))
            self.assertFalse(blocked['resolved'])
            self.assertIn('Settings-write', blocked['retryBlocked'])
            self.assertEqual(blocked['result_json'], result)

    def test_auto_history_matches_source_resolution_and_preserves_results(self):
        import sys
        from types import SimpleNamespace
        engine = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(engine))
        from backend.jobs import JobQueue
        token = 'a'*32
        cases = [
            '{"stages":{"curator":{"status":"failed"}}}',
            '{"stages":{"scoring":{"status":"failed"},"curator":{"status":"failed"}}}',
            '{"stages":{"curator":{"status":"failed"},"editor":{"status":"failed"}}}',
            '{"stages":{"curator":{"status":"failed","status":"ready"}}}',
            '{"stages":{"curator":{"status":"ready"},"curator":{"status":"failed"}}}',
            '{"stages":{"curator":{"status":"failed"}},"stages":null}',
            '{"stages":{"editor":{"status":"failed"}},"ignored":{"text":"\\q"}}',
            '{"stages":[{"curator":{"status":"failed"}}]}',
            '{"stages":{"unknown":{"status":"failed"}}}',
            '{"stages":{"\\u0063urator":{"status":"f\\u0061iled"}},"ignored":"'+('x'*(8*1024*1024))+'"}',
        ]
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)/'data'
            command = [str(engine/'.prepared/python/bin/python3'), str(engine/'stdio_service.py'), str(data)]
            env = {'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
            subprocess.run(command, input=json.dumps({'token':token})+'\n', text=True, capture_output=True, check=True, env=env)
            item = 'item'+'x'*70000
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES (?,'news','t','01','01','01','01')", (item,))
                db.execute("INSERT INTO curator_runs(id,item_id,status,started_at,finished_at) VALUES ('curator-success',?,'succeeded','02','03')", (item,))
                db.execute("INSERT INTO pipeline_stage_runs(job_id,item_id,stage,status,updated_at) VALUES ('scoring-success',?,'scoring','ready','03')", (item,))
                db.executemany("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,result_json) VALUES (?,?,'auto',?,'failed','01','01',?,?)", [(str(i),item,str(i),'99' if i == 1 else '01',value) for i,value in enumerate(cases)])
            with closing(sqlite3.connect(data/'information.sqlite')) as db:
                db.row_factory = sqlite3.Row
                queue = JobQueue(SimpleNamespace(db=db))
                expected = {row['id']:queue.failure_resolved(row) for row in db.execute("SELECT * FROM processing_jobs")}
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            def send(value):
                process.stdin.write(json.dumps(value)+'\n'); process.stdin.flush()
                return json.loads(process.stdout.readline())
            try:
                self.assertEqual(send({'token':token}), {'status':'ready'})
                cursor = None; chunks = bytearray(); records = {}
                while True:
                    page = send({'id':1,'token':token,'method':'GET','path':'/api/jobs','query':{} if cursor is None else {'cursor':cursor}})['result']
                    chunks.extend(base64.b64decode(page['chunk']))
                    if page['recordComplete']:
                        record = json.loads(chunks); chunks.clear(); records[record['id']] = record
                    cursor = page['next']
                    if cursor is None: break
                self.assertEqual(set(records), set(expected))
                for job_id, resolved in expected.items():
                    self.assertEqual(records[job_id]['resolved'], resolved)
                    self.assertEqual(records[job_id]['result_json'], cases[int(job_id)])
                    self.assertEqual(records[job_id]['item_id'], item)
                    self.assertFalse(records[job_id]['retryable'])
            finally:
                process.stdin.close(); self.assertEqual(process.wait(timeout=10), 0)
                process.stdout.close(); process.stderr.close()

    def test_history_traverses_the_full_signed_rowid_range(self):
        engine = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'data'
            command = [str(engine / '.prepared/python/bin/python3'), str(engine / 'stdio_service.py'), str(data)]
            token = 'a' * 32
            env = {'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
            subprocess.run(command, input=json.dumps({'token':token})+'\n', text=True, capture_output=True, check=True, env=env, timeout=10)
            values = [(2**63-1, 'max'), (1, 'positive'), (0, 'zero'), (-1, 'negative'), (-2**63, 'min')]
            with closing(sqlite3.connect(data / 'information.sqlite')) as db, db:
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news','Synthetic','now','now','now','now')")
                db.executemany("INSERT INTO processing_jobs(rowid,id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at) VALUES (?,?,'item','curator',?,'succeeded','now','now','now')", [(rowid, name, name) for rowid, name in values])
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
            def send(message):
                process.stdin.write(json.dumps(message)+'\n'); process.stdin.flush()
                return json.loads(process.stdout.readline())
            try:
                self.assertEqual(send({'token':token}), {'status':'ready'})
                cursor = None
                records = []
                while True:
                    response = send({'id':1,'token':token,'method':'GET','path':'/api/jobs','query':{} if cursor is None else {'cursor':cursor}})
                    self.assertIn('result', response, response)
                    page = response['result']
                    self.assertTrue(page['recordComplete'])
                    records.append(json.loads(base64.b64decode(page['chunk'])))
                    cursor = page['next']
                    if cursor is None:
                        break
                self.assertEqual([record['id'] for record in records], [name for _, name in values])
                for rowid in (-2**63-1, 2**63):
                    self.assertEqual(send({'id':2,'token':token,'method':'GET','path':'/api/jobs','query':{'cursor':f'{rowid}:0:-'}})['error'], 'invalid query')
            finally:
                process.stdin.close()
                process.wait(timeout=10)
                process.stdout.close()

    def test_complete_history_and_large_unicode_record(self):
        engine = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'data'
            token = 'a' * 32
            process = subprocess.Popen([str(engine / '.prepared/python/bin/python3'), str(engine / 'stdio_service.py'), str(data)],
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                                       env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'})
            def send(message):
                process.stdin.write(json.dumps(message)+'\n'); process.stdin.flush()
                return json.loads(process.stdout.readline())
            self.assertEqual(send({'token':token}), {'status':'ready'})
            title = '长😀\\"' * 20000
            error = '错误😀' * 24000
            stored_result = json.dumps({'detail': '结果😀' * 20000}, ensure_ascii=False)
            with closing(sqlite3.connect(data / 'information.sqlite')) as db, db:
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news',?,'2026','2026','2026','2026')", (title,))
                db.executemany("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,error) VALUES (?,'item','curator',?,'failed','2026','2026','2026',?)", [(str(i),str(i), error if i == 0 else 'error') for i in range(205)])
                db.execute("UPDATE processing_jobs SET result_json=? WHERE id='0'", (stored_result,))
            cursor = None
            records = []
            chunks = bytearray()
            while True:
                query = {} if cursor is None else {'cursor': cursor}
                reply = send({'id':1,'token':token,'method':'GET','path':'/api/jobs','query':query})
                result = reply['result']
                chunks.extend(base64.b64decode(result['chunk']))
                if result['recordComplete']:
                    records.append(json.loads(chunks)); chunks.clear()
                cursor = result['next']
                if cursor is None: break
            self.assertEqual(len(records),205)
            self.assertEqual(len({r['id'] for r in records}),205)
            self.assertEqual(next(r for r in records if r['id']=='0')['error'], error)
            self.assertEqual(next(r for r in records if r['id']=='0')['result_json'], stored_result)
            self.assertTrue(all(r['title']==title for r in records))
            for query in ({'cursor':'garbage'}, {'cursor':{}}, {'limit': 2}, {'cursor':'1:0:bad'}, {'cursor':'999999:0:-'}):
                self.assertEqual(send({'id':2,'token':token,'method':'GET','path':'/api/jobs','query':query})['error'], 'invalid query')
            first_frame = send({'id':3,'token':token,'method':'GET','path':'/api/jobs','query':{}})['result']
            saved = first_frame['next']
            self.assertIsNotNone(saved)
            with closing(sqlite3.connect(data / 'information.sqlite')) as db, db:
                db.execute("UPDATE items SET title='changed' WHERE id='item'")
            old = bytearray(base64.b64decode(first_frame['chunk']))
            while saved:
                frame = send({'id':4,'token':token,'method':'GET','path':'/api/jobs','query':{'cursor':saved}})['result']
                old.extend(base64.b64decode(frame['chunk']))
                if frame['recordComplete']: break
                saved = frame['next']
            self.assertEqual(json.loads(old)['title'], title)
            fresh = send({'id':5,'token':token,'method':'GET','path':'/api/jobs','query':{}})['result']
            self.assertEqual(json.loads(base64.b64decode(fresh['chunk']))['title'], 'changed')
            process.stdin.close(); self.assertEqual(process.wait(timeout=10),0)
            process.stdout.close()
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                self.assertEqual(db.execute('SELECT count(*) FROM processing_jobs').fetchone()[0],205)
