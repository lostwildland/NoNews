import base64
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest


class JobsPagingTest(unittest.TestCase):
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
            self.assertEqual(send({'id':4,'token':token,'method':'GET','path':'/api/jobs','query':{'cursor':saved}})['error'], 'invalid query')
            process.stdin.close(); self.assertEqual(process.wait(timeout=10),0)
            process.stdout.close()
            with sqlite3.connect(data/'information.sqlite') as db:
                self.assertEqual(db.execute('SELECT count(*) FROM processing_jobs').fetchone()[0],205)
