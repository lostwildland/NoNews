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
