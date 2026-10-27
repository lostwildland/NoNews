import sqlite3
import sys
from pathlib import Path

payload = Path(sys.argv[1])
sys.path.insert(0, str(payload))
from backend.server import Application
root = Path(sys.argv[2])
Application(root / 'information.sqlite', root / 'raw', root / 'artifacts', token='a'*32, write_scope='settings')
with sqlite3.connect(root / 'information.sqlite') as db:
    db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('item','news',?,'2026','2026','2026','2026')", ('x'*20000,))
    db.executemany("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,error) VALUES (?,'item','curator',?,'failed','2026','2026','2026',?)", [(str(i), str(i), 'e'*20000) for i in range(201)])
    deep = '['*500000 + '0' + ']'*500000
    stages = '"stages":{"curator":{"status":"failed"}}'
    db.execute("UPDATE processing_jobs SET stage='auto',result_json=? WHERE id='200'", ('{"ignored":'+deep+','+stages+'}',))
    db.execute("UPDATE processing_jobs SET stage='auto',result_json=? WHERE id='199'", ('{"ignored":'+deep[:-1]+','+stages+'}',))
    db.execute("INSERT INTO curator_runs(id,item_id,status,started_at,finished_at) VALUES ('success','item','succeeded','2027','2027')")
