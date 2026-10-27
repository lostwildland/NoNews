import base64
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest


class JobsPagingTest(unittest.TestCase):
    def test_history_traverses_the_full_signed_rowid_range(self):
        engine = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'data'
            command = [str(engine / '.prepared/python/bin/python3'), str(engine / 'stdio_service.py'), str(data)]
            token = 'a' * 32
            env = {'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
            subprocess.run(command, input=json.dumps({'token':token})+'\n', text=True, capture_output=True, check=True, env=env, timeout=10)
            values = [(2**63-1, 'max'), (1, 'positive'), (0, 'zero'), (-1, 'negative'), (-2**63, 'min')]
            with sqlite3.connect(data / 'information.sqlite') as db:
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
            with sqlite3.connect(data / 'information.sqlite') as db:
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
            with sqlite3.connect(data / 'information.sqlite') as db:
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
            with sqlite3.connect(data/'information.sqlite') as db:
                self.assertEqual(db.execute('SELECT count(*) FROM processing_jobs').fetchone()[0],205)
