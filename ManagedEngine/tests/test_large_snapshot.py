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
    def test_eight_megabyte_record_is_serialized_once_and_consistent(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp) / 'data'
            token = 'a'*32
            script = root / 'stdio_service.py'
            bootstrap = subprocess.run([sys.executable,str(script),str(data)],input=json.dumps({'token':token})+'\n',text=True,capture_output=True,check=True)
            with closing(sqlite3.connect(data/'information.sqlite')) as db, db:
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news','old','now','now','now','now')")
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,result_json) VALUES ('job','item','curator','key','succeeded','now','now','now',?)", ('x'*(8*1024*1024),))
            code = '''import sys,json
sys.path.insert(0,sys.argv[1])
from backend.server import Application
from pathlib import Path
import backend.server as server
root=Path(sys.argv[2]); app=Application(root/'information.sqlite',root/'raw',root/'artifacts',token='a'*32,write_scope='settings')
original=server.json.dumps
count=0
def counted(*a,**kw):
 global count
 count+=1
 return original(*a,**kw)
server.json.dumps=counted
first=app.handle('GET','/api/jobs',{},{}); frames=[first['chunk']]; cursor=first['next']
import sqlite3
with sqlite3.connect(root/'information.sqlite') as db: db.execute("UPDATE items SET title='new'")
while cursor:
 item=app.handle('GET','/api/jobs',{'cursor':cursor},{})
 frames.append(item['chunk']); cursor=item['next']
print(json.dumps({'count':count,'frames':frames},separators=(',',':')))
'''
            p = subprocess.run([sys.executable,'-c',code,str(root),str(data)],capture_output=True,text=True,check=True,timeout=30)
            result=json.loads(p.stdout)
            self.assertEqual(result['count'],1)
            record=json.loads(b''.join(base64.b64decode(x) for x in result['frames']))
            self.assertEqual(record['title'],'old')
            self.assertEqual(len(record['result_json']),8*1024*1024)
            expiry = '''import sys,time
sys.path.insert(0,sys.argv[1])
import backend.server as server
from pathlib import Path
original=server.threading.Timer
server.threading.Timer=lambda interval,fn,args: original(0.05,fn,args=args)
root=Path(sys.argv[2]); app=server.Application(root/'information.sqlite',root/'raw',root/'artifacts',token='a'*32,write_scope='settings')
frame=app.handle('GET','/api/jobs',{},{}); time.sleep(0.2)
try: app.handle('GET','/api/jobs',{'cursor':frame['next']},{})
except ValueError: print('expired')
'''
            expired=subprocess.run([sys.executable,'-c',expiry,str(root),str(data)],capture_output=True,text=True,check=True,timeout=10)
            self.assertEqual(expired.stdout.strip(),'expired')
