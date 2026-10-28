"""Measure synthetic public preview and full page traversal in a fresh process."""
import base64
from contextlib import closing
import gc
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import resource
import sqlite3
import sys
import tempfile
from threading import Thread
import tracemalloc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.server import Application


class Directory(BaseHTTPRequestHandler):
    def do_GET(self):
        data = b'{"data":[{"id":"old/model"}]}'
        self.send_response(200)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_):
        pass


def main():
    count = int(sys.argv[1])
    server = ThreadingHTTPServer(('127.0.0.1', 0), Directory)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application(root / 'information.sqlite', root / 'raw', root / 'artifacts', token='a' * 32, write_scope='settings')
            service = app.handle('PUT', '/api/config/services', {}, {'name': 'Fixture', 'type': 'magpie',
                                 'endpoint': f'http://127.0.0.1:{server.server_port}'})
            app.handle('POST', '/api/config/refresh', {}, {'id': service['id']})
            with closing(sqlite3.connect(root / 'information.sqlite')) as db, db:
                db.execute("INSERT INTO items(id,media_type,title,first_ingested_at,review_date,created_at,updated_at) VALUES ('fixture-item','news','Fixture','now','now','now','now')")
                db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,editor_target) VALUES ('fixture-job','fixture-item','editor','fixture-job','pending','now','now','now','fixture/pinned')")
                db.executemany('INSERT INTO model_configs VALUES (?,?,?,?)',
                    ((f'fixture-{index:05}-' + 'x' * 8_000, 'curator', '{"provider":"old","model":"model"}', 'now') for index in range(count)))
            gc.collect()
            tracemalloc.start()
            page = app.handle('POST', '/api/config/migration/preview', {},
                              {'serviceId': service['id'], 'editorServices': {'fixture-job': service['id']}})
            total, pages = 0, 0
            while 'chunk' in page:
                total += len(base64.b64decode(page['chunk']))
                pages += 1
                if page['next'] is None:
                    break
                page = app.handle('POST', '/api/config/migration/preview', {}, page['next'])
            if not pages:
                total = len(json.dumps(page, separators=(',', ':')).encode())
            current, peak = tracemalloc.get_traced_memory()
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            print(json.dumps({'rows': count, 'reportBytes': total, 'pages': pages, 'pythonCurrentBytes': current,
                              'pythonPeakBytes': peak, 'processMaxRSSRaw': rss,
                              'rssUnit': 'bytes' if sys.platform == 'darwin' else 'KiB'}))
            tracemalloc.stop()
            app.close()
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


if __name__ == '__main__':
    main()
