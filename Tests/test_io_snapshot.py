import hashlib
from contextlib import closing
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.io_snapshot import SnapshotError, snapshot, verify, restore


class SnapshotTests(unittest.TestCase):
    def test_private_raw_requires_matching_root_hash_size_and_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            private = root / 'private'
            private.mkdir()
            (private / 'raw').write_bytes(b'private synthetic')
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                db.executescript('''
                    CREATE TABLE raw_snapshots (id INTEGER PRIMARY KEY, item_id TEXT NOT NULL, path TEXT NOT NULL);
                    CREATE TABLE private_raw_sources (snapshot_id INTEGER PRIMARY KEY, item_id TEXT NOT NULL, relative_path TEXT NOT NULL, sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL);
                    INSERT INTO raw_snapshots VALUES (1,'item','');
                ''')
                db.execute('INSERT INTO private_raw_sources VALUES (1,?,?,?,?)', ('item','raw',hashlib.sha256(b'private synthetic').hexdigest(),17))
            with self.assertRaises(SnapshotError):
                snapshot(root / 'source.sqlite', {'vault': vault}, root / 'snap')
            snapshot(root / 'source.sqlite', {'vault': vault, 'private_raw': private}, root / 'snap')
            restore(root / 'snap', root / 'out')
            self.assertEqual((root / 'out/assets/private_raw/raw').read_bytes(), b'private synthetic')
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                db.execute("UPDATE private_raw_sources SET item_id='wrong'")
            with self.assertRaisesRegex(SnapshotError, 'identity mismatch'):
                snapshot(root / 'source.sqlite', {'vault': vault, 'private_raw': private}, root / 'other')

    def test_cli_rejects_tampered_database_and_untrusted_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = self.make_simple(root)
            cli = Path(__file__).parents[1] / 'scripts/io_snapshot.py'
            def run(*args):
                return subprocess.run([sys.executable, str(cli), *map(str, args)], capture_output=True, text=True)
            self.assertEqual(run('snapshot', root / 'source.sqlite', root / 'snap', '--root', f'vault={assets}').returncode, 0)
            self.assertEqual(run('verify', root / 'snap').returncode, 0)
            manifest_path = root / 'snap/manifest.json'
            manifest = json.loads(manifest_path.read_text())
            manifest['assets']['../escape'] = manifest['assets'].pop('vault')
            manifest_path.write_text(json.dumps(manifest))
            self.assertEqual(run('restore', root / 'snap', root / 'out').returncode, 1)
            self.assertFalse((root / 'out').exists())
            manifest['assets']['vault'] = manifest['assets'].pop('../escape')
            manifest_path.write_text(json.dumps(manifest))
            (root / 'snap/database.sqlite').write_bytes(b'corrupt')
            self.assertEqual(run('verify', root / 'snap').returncode, 1)

    def test_interrupted_publication_cannot_overwrite_or_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = self.make_simple(root)
            snapshot(root / 'source.sqlite', {'vault': assets}, root / 'snap')
            real_rename = os.rename
            calls = 0
            def interrupted(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError('simulated interruption')
                return real_rename(*args, **kwargs)
            with patch('scripts.io_snapshot.os.rename', side_effect=interrupted):
                with self.assertRaises(OSError):
                    restore(root / 'snap', root / 'out')
            with self.assertRaises(SnapshotError):
                verify(root / 'out')
            with self.assertRaises(SnapshotError):
                restore(root / 'snap', root / 'out')
            restore(root / 'snap', root / 'new')
            self.assertEqual((root / 'new/assets/vault/body').read_bytes(), b'synthetic')

    def test_asset_change_during_backup_is_refused(self):
        import scripts.io_snapshot as io_snapshot
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = self.make_simple(root)
            original = io_snapshot._backup
            calls = 0
            def changing(source, target):
                nonlocal calls
                original(source, target)
                calls += 1
                if calls == 1:
                    (assets / 'body').write_bytes(b'changed')
            with patch('scripts.io_snapshot._backup', side_effect=changing):
                with self.assertRaisesRegex(SnapshotError, 'source changed'):
                    snapshot(root / 'source.sqlite', {'vault': assets}, root / 'snap')
            self.assertFalse((root / 'snap').exists())

    def test_database_change_during_backup_is_refused(self):
        import scripts.io_snapshot as io_snapshot
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = self.make_simple(root)
            original = io_snapshot._backup
            calls = 0
            def changing(source, target):
                nonlocal calls
                original(source, target)
                calls += 1
                if calls == 1:
                    with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                        db.execute("INSERT INTO schema_meta VALUES ('synthetic-change','1')")
            with patch('scripts.io_snapshot._backup', side_effect=changing):
                with self.assertRaisesRegex(SnapshotError, 'source changed'):
                    snapshot(root / 'source.sqlite', {'vault': assets}, root / 'snap')
            self.assertFalse((root / 'snap').exists())

    def test_source_schema_versions_jobs_receipts_and_authority_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / 'vault'
            vault.mkdir()
            body = b'synthetic authoritative body'
            draft = b'synthetic authoritative draft'
            (vault / 'body.md').write_bytes(body)
            (vault / 'draft.md').write_bytes(draft)
            db = sqlite3.connect(root / 'source.sqlite')
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript((Path(__file__).parent / 'fixtures/io-v41.sql').read_text())
            db.executescript('''
                INSERT INTO schema_meta VALUES ('schema_version','41');
                INSERT INTO items (id, media_type, first_ingested_at, review_date, created_at, updated_at) VALUES ('item','paper','now','now','now','now');
                INSERT INTO item_identities VALUES (1,'item','paper','doi','synthetic-doi','now');
                INSERT INTO raw_snapshots VALUES (1,'item','old-ref','source','now','now','');
                INSERT INTO editor_drafts (id,item_id,raw_snapshot_id,created_at) VALUES ('draft','item',1,'now');
                INSERT INTO literature_files VALUES ('item','key','active','synthetic','{}','writer','now','now');
                INSERT INTO processing_jobs (id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,intent_json) VALUES ('job','item','edit','once','pending','now','now','now','{"synthetic":true}');
                INSERT INTO ai_feed_settings (freshrss_feed_id,last_seen_at,updated_at) VALUES ('feed','now','now');
                INSERT INTO app_settings VALUES ('setting','synthetic','now');
                INSERT INTO media_upload_intents VALUES ('object','item','item','image','{}',X'0001FF','now');
                INSERT INTO media_receipts (id,owner_kind,owner_id,status,created_at) VALUES (1,'item','item','uploaded','now');
                INSERT INTO media_objects (key,namespace,sha256,stored_sha256,ext,bytes,public_url,created_at) VALUES ('object','test','hash','hash','png',3,'https://example.invalid/object','now');
                INSERT INTO media_raw_activation_intents (id,item_id,old_mapping_json,old_authority_json,citekey,candidate_hash,state) VALUES ('intent','item','{}','{}','key','hash','complete');
                CREATE TABLE "future table" (identity TEXT, payload BLOB);
                INSERT INTO "future table" VALUES ('future',X'00FF');
            ''')
            db.execute('INSERT INTO literature_raws VALUES (1,?,?,?,?,?)', ('item','key','body.md',hashlib.sha256(body).hexdigest(),'now'))
            db.execute('INSERT INTO literature_drafts VALUES (?,?,?,?,?,?,?,?,?,?)', ('draft','item','key','identity','file-id','draft.md',1,'payload',hashlib.sha256(draft).hexdigest(),'now'))
            db.execute("INSERT INTO body_versions (snapshot_id,item_id,sha256,characters,authority,source,retrieved_at,stored_at) VALUES (1,'item',?, ?, 'imported','synthetic','now','now')", (hashlib.sha256(body).hexdigest(),len(body)))
            db.execute('INSERT INTO body_texts VALUES (1,?)', (body.decode(),))
            db.execute("INSERT INTO draft_versions VALUES ('draft','item',?,?,'imported','now',NULL,NULL)", (hashlib.sha256(draft).hexdigest(),len(draft)))
            db.execute('INSERT INTO draft_bodies VALUES (?,?)', ('draft',draft.decode()))
            db.commit()
            snapshot(root / 'source.sqlite', {'vault': vault}, root / 'snap')
            report = verify(root / 'snap')
            self.assertEqual(report['remote_reference_counts'], {'media_objects': 1, 'media_receipts': 1, 'media_upload_intents': 1})
            restore(root / 'snap', root / 'out')
            with closing(sqlite3.connect(root / 'out/database.sqlite')) as result:
                schema = db.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
                self.assertEqual(schema, result.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall())
                for name, _ in schema:
                    quoted = '"' + name.replace('"', '""') + '"'
                    self.assertCountEqual(db.execute('SELECT * FROM ' + quoted).fetchall(), result.execute('SELECT * FROM ' + quoted).fetchall(), name)
                self.assertEqual(result.execute('SELECT authority FROM body_versions').fetchone(), ('imported',))
                self.assertEqual(result.execute('SELECT identity_value FROM item_identities').fetchone(), ('synthetic-doi',))
                self.assertEqual(result.execute('SELECT intent_json FROM processing_jobs').fetchone(), ('{"synthetic":true}',))
                self.assertEqual(result.execute('SELECT payload FROM media_upload_intents').fetchone(), (b'\x00\x01\xff',))
                self.assertEqual(result.execute('SELECT payload FROM "future table"').fetchone(), (b'\x00\xff',))
            db.close()
            self.assertEqual((root / 'out/assets/vault/draft.md').read_bytes(), draft)

    def make_simple(self, root):
        assets = root / 'vault'
        assets.mkdir()
        (assets / 'body').write_bytes(b'synthetic')
        db = sqlite3.connect(root / 'source.sqlite')
        db.executescript("CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL); INSERT INTO schema_meta VALUES ('schema_version','41');")
        db.close()
        return assets

    def test_tampering_and_existing_destination_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = self.make_simple(root)
            snapshot(root / 'source.sqlite', {'vault': assets}, root / 'snap')
            restore(root / 'snap', root / 'out')
            with self.assertRaises(SnapshotError):
                restore(root / 'snap', root / 'out')
            (root / 'snap/assets/vault/body').write_bytes(b'altered')
            with self.assertRaises(SnapshotError):
                verify(root / 'snap')
            with self.assertRaises(SnapshotError):
                restore(root / 'snap', root / 'new')
            self.assertFalse((root / 'new').exists())
            self.assertEqual((root / 'out/assets/vault/body').read_bytes(), b'synthetic')

    def test_missing_changed_and_unsafe_references_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = self.make_simple(root)
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                db.execute('CREATE TABLE literature_raws (snapshot_id INTEGER PRIMARY KEY, item_id TEXT NOT NULL, citekey TEXT NOT NULL, path TEXT NOT NULL, file_sha256 TEXT NOT NULL, bound_at TEXT NOT NULL)')
                db.execute('INSERT INTO literature_raws VALUES (1, ?, ?, ?, ?, ?)', ('item', 'key', '../outside', hashlib.sha256(b'synthetic').hexdigest(), 'now'))
            with self.assertRaises(SnapshotError):
                snapshot(root / 'source.sqlite', {'vault': assets}, root / 'snap')
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                db.execute("UPDATE literature_raws SET path='body', file_sha256='wrong'")
            with self.assertRaises(SnapshotError):
                snapshot(root / 'source.sqlite', {'vault': assets}, root / 'snap')
            self.assertFalse((root / 'snap').exists())

    def test_symlinks_and_interrupted_destination_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = self.make_simple(root)
            (assets / 'link').symlink_to(root / 'source.sqlite')
            with self.assertRaises(SnapshotError):
                snapshot(root / 'source.sqlite', {'vault': assets}, root / 'snap')
            (assets / 'link').unlink()
            snapshot(root / 'source.sqlite', {'vault': assets}, root / 'snap')
            (root / 'interrupted').mkdir()
            (root / 'interrupted/partial').write_text('keep')
            with self.assertRaises(SnapshotError):
                restore(root / 'snap', root / 'interrupted')
            self.assertEqual((root / 'interrupted/partial').read_text(), 'keep')
            (root / 'snap/assets/vault/body').unlink()
            (root / 'snap/assets/vault/body').symlink_to(root / 'source.sqlite')
            with self.assertRaises(SnapshotError):
                restore(root / 'snap', root / 'other')

    def test_unknown_raw_and_pending_media_are_not_silently_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = self.make_simple(root)
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                db.executescript("CREATE TABLE raw_snapshots (id INTEGER PRIMARY KEY, path TEXT); INSERT INTO raw_snapshots VALUES (1, 'old');")
            with self.assertRaisesRegex(SnapshotError, 'unresolved raw'):
                snapshot(root / 'source.sqlite', {'vault': assets}, root / 'snap')
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                db.executescript('DELETE FROM raw_snapshots; CREATE TABLE media_pending (id INTEGER PRIMARY KEY, staging_path TEXT NOT NULL); INSERT INTO media_pending VALUES (1, \'unknown\');')
            with self.assertRaisesRegex(SnapshotError, 'media staging'):
                snapshot(root / 'source.sqlite', {'vault': assets}, root / 'snap')

    def test_wal_and_file_authority_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = root / 'vault'
            (assets / 'raw').mkdir(parents=True)
            body = b'Synthetic file-authoritative body\n'
            (assets / 'raw/body.md').write_bytes(body)
            db = sqlite3.connect(root / 'source.sqlite')
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript('''
                CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE items (id TEXT PRIMARY KEY);
                CREATE TABLE raw_snapshots (id INTEGER PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id), path TEXT NOT NULL, source_hash TEXT NOT NULL, retrieved_at TEXT NOT NULL, created_at TEXT NOT NULL, provenance TEXT NOT NULL DEFAULT '', UNIQUE(item_id, source_hash));
                CREATE TABLE literature_raws (snapshot_id INTEGER PRIMARY KEY REFERENCES raw_snapshots(id), item_id TEXT NOT NULL REFERENCES items(id), citekey TEXT NOT NULL, path TEXT NOT NULL, file_sha256 TEXT NOT NULL, bound_at TEXT NOT NULL);
                CREATE TABLE future_table (id TEXT PRIMARY KEY, payload BLOB);
                INSERT INTO schema_meta VALUES ('schema_version', '41');
                INSERT INTO items VALUES ('synthetic-item');
                INSERT INTO raw_snapshots VALUES (1, 'synthetic-item', '', 'source', 'now', 'now', '');
                INSERT INTO future_table VALUES ('opaque', X'000102FF');
            ''')
            db.execute('INSERT INTO literature_raws VALUES (1, ?, ?, ?, ?, ?)', ('synthetic-item', 'key', 'raw/body.md', hashlib.sha256(body).hexdigest(), 'now'))
            db.commit()
            snapshot(root / 'source.sqlite', {'vault': assets}, root / 'snapshot')
            verify(root / 'snapshot')
            restore(root / 'snapshot', root / 'restored')
            db.close()
            with closing(sqlite3.connect(root / 'restored/database.sqlite')) as restored:
                self.assertEqual(restored.execute('SELECT * FROM future_table').fetchall(), [('opaque', b'\x00\x01\x02\xff')])
                self.assertEqual(restored.execute('SELECT item_id, path FROM literature_raws').fetchall(), [('synthetic-item', 'raw/body.md')])
                self.assertEqual(restored.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone(), ('41',))
            self.assertEqual((root / 'restored/assets/vault/raw/body.md').read_bytes(), body)


if __name__ == '__main__':
    unittest.main()
