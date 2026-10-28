"""Populate synthetic migration rows for the standalone native client check."""
import json
import sqlite3
import sys

with sqlite3.connect(sys.argv[1]) as db:
    if len(sys.argv) > 2:
        db.execute("DELETE FROM model_configs WHERE kit_id=?", ('native-0000-' + 'x' * 8000,))
    else:
        db.executemany('INSERT INTO model_configs VALUES (?,?,?,?)',
                       ((f'native-{index:04}-' + 'x' * 8000, 'curator', '{"provider":"fixture","model":"Exact"}', 'now') for index in range(2200)))
        db.execute('INSERT INTO app_settings VALUES (?,?,?)',
                   ('magpie_migration_evidence', json.dumps([{'detail': '文' * 30000}]), 'now'))
