"""Hold a synthetic SQLite write lock until the native test releases stdin."""
import sqlite3
import sys

with sqlite3.connect(sys.argv[1]) as db:
    db.execute('BEGIN IMMEDIATE')
    print('locked', flush=True)
    sys.stdin.readline()
    db.rollback()
