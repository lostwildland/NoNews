import hashlib
import gzip
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

from scripts.io_snapshot import SnapshotError, snapshot, verify, restore, read_asset, recovery_binding, read_recovery_asset, recovery_adapter, remote_references


class SnapshotTests(unittest.TestCase):
    def test_schema_semantic_constraints_are_required_for_snapshot_and_verify(self):
        for defect, operation in ((d, op) for d in ('missing-index', 'wrong-index', 'wrong-expression-index', 'missing-check', 'missing-primary-key', 'missing-unique', 'missing-foreign-key', 'missing-not-null') for op in ('snapshot', 'verify')):
            with self.subTest(defect=defect, operation=operation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                vault = self.make_simple(root)
                snapshot(root / 'source.sqlite', {'vault': vault}, root / 'good')
                for database, destination in ((root / 'source.sqlite', root / 'bad'),) if operation == 'snapshot' else ((root / 'good/database.sqlite', None),):
                    with closing(sqlite3.connect(database)) as db, db:
                        if defect in ('missing-index', 'wrong-index', 'wrong-expression-index'):
                            db.execute('DROP INDEX media_document_one_pending')
                            if defect == 'wrong-index':
                                db.execute("CREATE UNIQUE INDEX media_document_one_pending ON media_document_generations(item_id) WHERE state='committed'")
                            elif defect == 'wrong-expression-index':
                                db.execute("CREATE UNIQUE INDEX media_document_one_pending ON media_document_generations(item_id, lower(generation)) WHERE state='pending'")
                        elif defect == 'missing-check':
                            ddl = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='media_document_generations'").fetchone()[0]
                            index_ddl = db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='media_document_one_pending'").fetchone()[0]
                            self.assertIn("CHECK(state IN ('pending','committed'))", ddl)
                            db.execute('DROP TABLE media_document_generations')
                            db.execute(ddl.replace("CHECK(state IN ('pending','committed'))", ''))
                            db.execute(index_ddl)
                        elif defect == 'missing-primary-key':
                            db.execute('DROP TABLE app_settings')
                            db.execute('CREATE TABLE app_settings(key TEXT, value TEXT NOT NULL, updated_at TEXT NOT NULL)')
                        elif defect == 'missing-not-null':
                            db.execute('DROP TABLE app_settings')
                            db.execute('CREATE TABLE app_settings(key TEXT PRIMARY KEY, value TEXT, updated_at TEXT NOT NULL)')
                        elif defect == 'missing-foreign-key':
                            db.execute('DROP TABLE body_texts')
                            db.execute('CREATE TABLE body_texts(snapshot_id INTEGER PRIMARY KEY, text TEXT NOT NULL)')
                        else:
                            ddl = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='media_pending'").fetchone()[0]
                            self.assertIn('UNIQUE(owner_kind, owner_id, source_ref)', ddl)
                            db.execute('DROP TABLE media_pending')
                            db.execute(ddl.replace(',\n        UNIQUE(owner_kind, owner_id, source_ref)', ''))
                    if destination:
                        with self.assertRaisesRegex(SnapshotError, 'required schema invariant'):
                            snapshot(database, {'vault': vault}, destination)
                    else:
                        manifest_file = root / 'good/manifest.json'
                        manifest = json.loads(manifest_file.read_text())
                        manifest['database_sha256'] = hashlib.sha256(database.read_bytes()).hexdigest()
                        manifest_file.write_text(json.dumps(manifest))
                        with self.assertRaisesRegex(SnapshotError, 'required schema invariant'):
                            verify(root / 'good')

    @staticmethod
    def init_schema(db):
        db.executescript((Path(__file__).parent / 'fixtures/io-v41-full.sql').read_text())
        db.execute("INSERT INTO schema_meta (key,value) VALUES ('schema_version','41')")
        db.executemany("INSERT INTO items (id,media_type,first_ingested_at,review_date,created_at,updated_at) VALUES (?,'paper','now','now','now','now')", [('item',), ('other',), ('retired',), ('wrong',)])

    @staticmethod
    def add_raw(db, item='item', path=''):
        db.execute("INSERT INTO raw_snapshots (id,item_id,path,source_hash,retrieved_at,created_at) VALUES (1,?,?, 'synthetic-source','now','now')", (item, path))

    @staticmethod
    def add_body(db, text, authority):
        db.execute("INSERT INTO body_versions (snapshot_id,item_id,sha256,characters,authority,source,retrieved_at,stored_at) VALUES (1,'item',?,?,?,'synthetic','now','now')", (hashlib.sha256(text.encode()).hexdigest(), len(text), authority))
        db.execute('INSERT INTO body_texts (snapshot_id,text) VALUES (1,?)', (text,))

    @staticmethod
    def add_file_authority(db, item='item'):
        db.execute("INSERT INTO literature_files (item_id,citekey,status,source,conditional_writer,enabled_at,updated_at) VALUES (?,'key','active','synthetic','writer','now','now')", (item,))

    def test_schema41_requires_complete_tables_and_columns(self):
        fixture = (Path(__file__).parent / 'fixtures/io-v41-full.sql').read_text()
        for defect in ('marker-only', 'missing-table', 'missing-column'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                vault = root / 'vault'
                vault.mkdir()
                with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                    if defect == 'marker-only':
                        db.execute('CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
                    else:
                        db.executescript(fixture)
                        if defect == 'missing-table':
                            db.execute('DROP TABLE app_settings')
                        else:
                            db.execute('ALTER TABLE app_settings DROP COLUMN updated_at')
                    db.execute("INSERT INTO schema_meta (key,value) VALUES ('schema_version','41')")
                message = {'marker-only': 'required schema table missing: activity',
                           'missing-table': 'required schema table missing: app_settings',
                           'missing-column': 'required schema column missing: app_settings.updated_at'}[defect]
                with self.assertRaisesRegex(SnapshotError, message):
                    snapshot(root / 'source.sqlite', {'vault': vault}, root / 'snap')
                self.assertFalse((root / 'snap').exists())

    def test_verify_rejects_missing_required_schema_even_with_valid_marker(self):
        fixture = (Path(__file__).parent / 'fixtures/io-v41-full.sql').read_text()
        for sql, message in (('DROP TABLE app_settings', 'required schema table missing: app_settings'),
                             ('ALTER TABLE app_settings DROP COLUMN updated_at', 'required schema column missing: app_settings.updated_at')):
            with self.subTest(defect=sql), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                vault = root / 'vault'
                vault.mkdir()
                with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                    db.executescript(fixture)
                    db.execute("INSERT INTO schema_meta (key,value) VALUES ('schema_version','41')")
                snapshot(root / 'source.sqlite', {'vault': vault}, root / 'snap')
                with closing(sqlite3.connect(root / 'snap/database.sqlite')) as db, db:
                    db.execute(sql)
                manifest_file = root / 'snap/manifest.json'
                manifest = json.loads(manifest_file.read_text())
                manifest['database_sha256'] = hashlib.sha256((root / 'snap/database.sqlite').read_bytes()).hexdigest()
                manifest_file.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(SnapshotError, message):
                    verify(root / 'snap')

    def test_schema_descriptor_matches_fixture_and_column_order_is_irrelevant(self):
        fixture = (Path(__file__).parent / 'fixtures/io-v41-full.sql').read_text()
        descriptor = json.loads((Path(__file__).parents[1] / 'scripts/io_schema41.json').read_text())
        with closing(sqlite3.connect(':memory:')) as db:
            db.executescript(fixture)
            expected = {name: sorted(row[1] for row in db.execute('PRAGMA table_info("' + name.replace('"', '""') + '")'))
                        for name, in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()}
            self.assertEqual(descriptor, expected)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                db.execute('DROP TABLE app_settings')
                db.execute('CREATE TABLE app_settings (updated_at TEXT NOT NULL, value TEXT NOT NULL, key TEXT PRIMARY KEY, extra TEXT)')
                db.execute("INSERT INTO app_settings (key,value,updated_at,extra) VALUES ('key','synthetic','now','extra')")
                ddl = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='media_document_generations'").fetchone()[0]
                self.assertIn("CHECK(state IN ('pending','committed'))", ddl)
                self.assertIn('PRIMARY KEY(item_id, generation)', ddl)
                db.execute('DROP TABLE media_document_generations')
                ddl = ddl.replace("CHECK(state IN ('pending','committed'))", 'CHECK ( ( "state" IN ( \'pending\' , \'committed\' ) ) )')
                db.execute(ddl.replace('PRIMARY KEY(item_id, generation)', 'PRIMARY KEY(generation, item_id)'))
                db.execute('CREATE UNIQUE INDEX replacement_pending ON media_document_generations ("item_id" COLLATE BINARY) WHERE ( "state" = \'pending\' )')
                db.execute('CREATE INDEX extra_lookup ON app_settings(value)')
                db.execute('CREATE UNIQUE INDEX extra_unique ON app_settings(extra)')
                db.execute('CREATE UNIQUE INDEX extra_expression ON app_settings(lower(value))')
                db.execute('CREATE TABLE "future table" (id TEXT, value BLOB)')
                db.execute("INSERT INTO \"future table\" VALUES ('new',X'00FF')")
            snapshot(root / 'source.sqlite', {'vault': vault}, root / 'snap')
            verify(root / 'snap')
            restore(root / 'snap', root / 'out')
            with closing(sqlite3.connect(root / 'out/database.sqlite')) as db:
                self.assertEqual(db.execute('SELECT key,value,extra FROM app_settings').fetchall(), [('key','synthetic','extra')])
                self.assertEqual(db.execute('SELECT id,value FROM "future table"').fetchall(), [('new',b'\x00\xff')])

    def test_cli_refuses_when_shipped_schema_descriptor_is_missing(self):
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            snapshot(root / 'source.sqlite', {'vault': vault}, root / 'valid')
            source_scripts = Path(__file__).parents[1] / 'scripts'
            isolated = root / 'isolated'
            isolated.mkdir()
            for name in ('io_snapshot.py', 'io_image_inventory.py'):
                shutil.copyfile(source_scripts / name, isolated / name)
            shutil.copytree(source_scripts / '_snapshot_vendor', isolated / '_snapshot_vendor', ignore=shutil.ignore_patterns('__pycache__'))
            result = subprocess.run([sys.executable, str(isolated / 'io_snapshot.py'), 'snapshot', str(root / 'source.sqlite'), str(root / 'snap'), '--root', f'vault={vault}'], cwd=isolated, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('required schema descriptor is unavailable', result.stdout)
            self.assertNotIn('Traceback', result.stderr)
            self.assertFalse((root / 'snap').exists())
            verified = subprocess.run([sys.executable, str(isolated / 'io_snapshot.py'), 'verify', str(root / 'valid')], cwd=isolated, capture_output=True, text=True)
            self.assertNotEqual(verified.returncode, 0)
            self.assertIn('required schema descriptor is unavailable', verified.stdout)
            (isolated / 'io_schema41.json').write_text('{}')
            result = subprocess.run([sys.executable, str(isolated / 'io_snapshot.py'), 'snapshot', str(root / 'source.sqlite'), str(root / 'snap'), '--root', f'vault={vault}'], cwd=isolated, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('required schema descriptor is invalid', result.stdout)
            self.assertFalse((root / 'snap').exists())
            shutil.copyfile(source_scripts / 'io_schema41.json', isolated / 'io_schema41.json')
            result = subprocess.run([sys.executable, str(isolated / 'io_snapshot.py'), 'snapshot', str(root / 'source.sqlite'), str(root / 'snap'), '--root', f'vault={vault}'], cwd=isolated, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('required schema descriptor is unavailable', result.stdout)
            (isolated / 'io_schema41_semantics.json').write_text('{}')
            result = subprocess.run([sys.executable, str(isolated / 'io_snapshot.py'), 'snapshot', str(root / 'source.sqlite'), str(root / 'snap'), '--root', f'vault={vault}'], cwd=isolated, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('required schema descriptor is invalid', result.stdout)

    def test_corrupt_deflate_is_refused_without_a_cli_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            archive = vault / 'source.html.gz'
            archive.write_bytes(b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03\x07' + b'\x00' * 8)
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                db.execute("INSERT INTO literature_assets (id,item_id,kind,source_path,archive_path,file_hash,metadata_json) VALUES (1,'item','publisher_html',?,?,?,?)", ('historical', str(archive), '0' * 64, '{}'))
            with self.assertRaisesRegex(SnapshotError, 'invalid compressed source'):
                snapshot(root / 'source.sqlite', {'vault': vault}, root / 'snap')
            cli = Path(__file__).parents[1] / 'scripts/io_snapshot.py'
            result = subprocess.run([sys.executable, str(cli), 'snapshot', str(root / 'source.sqlite'),
                                     str(root / 'cli-snap'), '--root', f'vault={vault}'],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('invalid compressed source', result.stdout)
            self.assertNotIn('Traceback', result.stderr)

    def test_blob_archive_path_is_refused_without_a_cli_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                db.execute("INSERT INTO literature_assets (id,item_id,kind,source_path,archive_path,file_hash,metadata_json) VALUES (1,'item','publisher_html',?,?,?,?)", ('historical', b'archive.gz', '0' * 64, '{}'))
            before = (root / 'source.sqlite').read_bytes()
            cli = Path(__file__).parents[1] / 'scripts/io_snapshot.py'
            result = subprocess.run([sys.executable, str(cli), 'snapshot', str(root / 'source.sqlite'),
                                     str(root / 'snap'), '--root', f'vault={vault}'],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('invalid required asset reference', result.stdout)
            self.assertNotIn('Traceback', result.stderr)
            self.assertFalse((root / 'snap').exists())
            self.assertEqual(before, (root / 'source.sqlite').read_bytes())

    def test_imported_raw_cannot_use_an_archive_in_place_of_its_file_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                self.add_raw(db, path=str(vault / 'body'))
                self.add_body(db, 'synthetic', 'imported')
                self.add_file_authority(db)
            with self.assertRaisesRegex(SnapshotError, 'imported raw.*authoritative file'):
                snapshot(root / 'source.sqlite', {'vault': vault}, root / 'snap')
            self.assertFalse((root / 'snap').exists())

    def test_wal_source_without_shm_is_never_modified(self):
        import shutil
        for mode in (0o755, 0o555):
            with self.subTest(directory_mode=oct(mode)), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                assets = root / 'vault'
                assets.mkdir()
                writer_dir = root / 'writer'
                writer_dir.mkdir()
                writer = sqlite3.connect(writer_dir / 'live.sqlite')
                try:
                    writer.execute('PRAGMA journal_mode=WAL')
                    writer.execute('PRAGMA wal_autocheckpoint=0')
                    self.init_schema(writer)
                    writer.executescript("CREATE TABLE future_table(id TEXT PRIMARY KEY, payload BLOB); INSERT INTO future_table VALUES ('wal-row',X'0001FF');")
                    source = root / 'source'
                    source.mkdir()
                    shutil.copyfile(writer_dir / 'live.sqlite', source / 'data.sqlite')
                    shutil.copyfile(writer_dir / 'live.sqlite-wal', source / 'data.sqlite-wal')
                    os.chmod(source, mode)
                    def state():
                        return {p.name: (p.read_bytes(), p.stat().st_mode & 0o777) for p in source.iterdir()}
                    before = state()
                    snapshot(source / 'data.sqlite', {'vault': assets}, root / 'snap')
                    self.assertEqual(state(), before)
                    self.assertEqual(source.stat().st_mode & 0o777, mode)
                    restore(root / 'snap', root / 'out')
                    with closing(sqlite3.connect(root / 'out/database.sqlite')) as db:
                        self.assertEqual(db.execute('SELECT * FROM future_table').fetchall(), [('wal-row', b'\x00\x01\xff')])
                finally:
                    if (root / 'source').exists():
                        os.chmod(root / 'source', 0o755)
                    writer.close()

    def test_wal_source_with_shm_bytes_and_modes_are_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = root / 'vault'
            assets.mkdir()
            source = root / 'source'
            source.mkdir()
            writer = sqlite3.connect(source / 'data.sqlite')
            try:
                writer.execute('PRAGMA journal_mode=WAL')
                writer.execute('PRAGMA wal_autocheckpoint=0')
                self.init_schema(writer)
                writer.executescript("CREATE TABLE future_table(id TEXT PRIMARY KEY); INSERT INTO future_table VALUES ('synthetic');")
                def state():
                    return {p.name: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mode & 0o777) for p in source.iterdir()}
                before = state()
                self.assertIn('data.sqlite-shm', before)
                snapshot(source / 'data.sqlite', {'vault': assets}, root / 'snap')
                self.assertEqual(state(), before)
                restore(root / 'snap', root / 'out')
                with closing(sqlite3.connect(root / 'out/database.sqlite')) as db:
                    self.assertEqual(db.execute('SELECT * FROM future_table').fetchall(), [('synthetic',)])
            finally:
                writer.close()

    def test_reused_wal_uses_stable_index_to_prove_committed_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / 'vault'
            vault.mkdir()
            writer = sqlite3.connect(root / 'source.sqlite')
            try:
                writer.execute('PRAGMA journal_mode=WAL')
                writer.execute('PRAGMA wal_autocheckpoint=0')
                self.init_schema(writer)
                writer.executescript('CREATE TABLE future_table(value BLOB);')
                for _ in range(10):
                    writer.execute('INSERT INTO future_table VALUES (?)', (b'x' * 8000,))
                    writer.commit()
                writer.execute('PRAGMA wal_checkpoint(RESTART)').fetchall()
                writer.execute('INSERT INTO future_table VALUES (?)', (b'after-restart',))
                writer.commit()
                sidecars = [root / 'source.sqlite', root / 'source.sqlite-wal', root / 'source.sqlite-shm']
                before = [(p.read_bytes(), p.stat().st_mode & 0o777) for p in sidecars]
                snapshot(root / 'source.sqlite', {'vault': vault}, root / 'snap')
                self.assertEqual([(p.read_bytes(), p.stat().st_mode & 0o777) for p in sidecars], before)
                restore(root / 'snap', root / 'out')
                with closing(sqlite3.connect(root / 'out/database.sqlite')) as db:
                    self.assertEqual(db.execute('SELECT count(*) FROM future_table').fetchone(), (11,))
                    self.assertEqual(db.execute('SELECT value FROM future_table ORDER BY rowid DESC LIMIT 1').fetchone(), (b'after-restart',))
            finally:
                writer.close()

    def test_mismatched_wal_index_is_refused(self):
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / 'vault'
            vault.mkdir()
            writer = sqlite3.connect(root / 'live.sqlite')
            try:
                writer.execute('PRAGMA journal_mode=WAL')
                writer.execute('PRAGMA wal_autocheckpoint=0')
                self.init_schema(writer)
                writer.commit()
                for suffix in ('', '-wal', '-shm'):
                    shutil.copyfile(root / ('live.sqlite' + suffix), root / ('copy.sqlite' + suffix))
                index = root / 'copy.sqlite-shm'
                content = bytearray(index.read_bytes())
                content[48] ^= 1
                index.write_bytes(content)
                with self.assertRaisesRegex(SnapshotError, 'inconsistent source WAL index'):
                    snapshot(root / 'copy.sqlite', {'vault': vault}, root / 'snap')
                self.assertFalse((root / 'snap').exists())
            finally:
                writer.close()

    def test_database_sidecars_reject_symlinks_special_files_and_journal(self):
        for suffix, kind in (('-wal', 'symlink'), ('-shm', 'symlink'), ('-wal', 'fifo'), ('-journal', 'file')):
            with self.subTest(suffix=suffix, kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                vault = self.make_simple(root)
                sidecar = root / ('source.sqlite' + suffix)
                if kind == 'symlink':
                    sidecar.symlink_to(root / 'source.sqlite')
                elif kind == 'fifo':
                    os.mkfifo(sidecar)
                else:
                    sidecar.write_bytes(b'synthetic journal')
                with self.assertRaisesRegex(SnapshotError, 'unsafe database sidecar|rollback journal'):
                    snapshot(root / 'source.sqlite', {'vault': vault}, root / 'snap')
                self.assertFalse((root / 'snap').exists())

    def test_source_change_during_file_copy_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            source = root / 'source.sqlite'
            inode = source.stat().st_ino
            real_read = os.read
            seen = 0
            def changing(fd, size):
                nonlocal seen
                data = real_read(fd, size)
                if data and os.fstat(fd).st_ino == inode:
                    seen += 1
                    if seen == 2:
                        with source.open('ab') as out:
                            out.write(b'concurrent change')
                return data
            with patch('scripts.io_snapshot.os.read', side_effect=changing):
                with self.assertRaisesRegex(SnapshotError, 'source changed'):
                    snapshot(source, {'vault': vault}, root / 'snap')
            self.assertFalse((root / 'snap').exists())

    def test_corrupted_wal_is_refused_before_private_recovery(self):
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = root / 'vault'
            assets.mkdir()
            writer = sqlite3.connect(root / 'live.sqlite')
            try:
                writer.execute('PRAGMA journal_mode=WAL')
                writer.execute('PRAGMA wal_autocheckpoint=0')
                self.init_schema(writer)
                writer.commit()
                shutil.copyfile(root / 'live.sqlite', root / 'copy.sqlite')
                shutil.copyfile(root / 'live.sqlite-wal', root / 'copy.sqlite-wal')
                wal = root / 'copy.sqlite-wal'
                data = bytearray(wal.read_bytes())
                data[-1] ^= 1
                wal.write_bytes(data)
                with self.assertRaisesRegex(SnapshotError, 'WAL.*checksum mismatch'):
                    snapshot(root / 'copy.sqlite', {'vault': assets}, root / 'snap')
                self.assertFalse((root / 'snap').exists())
                shutil.copyfile(root / 'live.sqlite-wal', wal)
                wal.write_bytes(wal.read_bytes()[:-1])
                with self.assertRaisesRegex(SnapshotError, 'incomplete source WAL frame'):
                    snapshot(root / 'copy.sqlite', {'vault': assets}, root / 'truncated')
                self.assertFalse((root / 'truncated').exists())
            finally:
                writer.close()

    def test_imported_draft_requires_authoritative_file_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            text = 'Synthetic imported draft'
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                db.execute("INSERT INTO editor_drafts (id,item_id,created_at) VALUES ('draft','item','now')")
                db.execute("INSERT INTO draft_versions (draft_id,item_id,sha256,characters,authority,stored_at) VALUES ('draft','item',?,?,'imported','now')", (hashlib.sha256(text.encode()).hexdigest(),len(text)))
                db.execute('INSERT INTO draft_bodies (draft_id,text) VALUES (?,?)', ('draft', text))
            with self.assertRaisesRegex(SnapshotError, 'imported draft.*authoritative file'):
                snapshot(root / 'source.sqlite', {'vault': vault}, root / 'missing')
            self.assertFalse((root / 'missing').exists())
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                self.assertEqual(db.execute('SELECT authority FROM draft_versions').fetchone(), ('imported',))
                db.execute("UPDATE draft_versions SET authority='database'")
            snapshot(root / 'source.sqlite', {'vault': vault}, root / 'database-authority')
            restore(root / 'database-authority', root / 'restored')
            with closing(sqlite3.connect(root / 'restored/database.sqlite')) as db:
                self.assertEqual(db.execute('SELECT text FROM draft_bodies').fetchone(), (text,))

    def test_managed_remote_object_requires_preserved_verified_bytes(self):
        for storage in ('file', 'database'):
            with self.subTest(storage=storage), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                vault = self.make_simple(root)
                payload = b'synthetic managed image'
                digest = hashlib.sha256(payload).hexdigest()
                with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                    db.execute("INSERT INTO media_objects (key,namespace,sha256,stored_sha256,ext,bytes,public_url,created_at) VALUES ('object','test',?,?,'png',?,'https://example.invalid/object','now')", (digest,digest,len(payload)))
                with self.assertRaisesRegex(SnapshotError, 'managed object.*preserved bytes'):
                    snapshot(root / 'source.sqlite', {'vault': vault}, root / 'missing')
                if storage == 'file':
                    (vault / 'object.png').write_bytes(b'wrong image bytes')
                else:
                    with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                        db.execute("INSERT INTO media_upload_intents (object_key,owner_kind,owner_id,source_ref,object_json,payload,created_at) VALUES ('object','item','item','image','{}',?,'now')", (b'wrong image bytes',))
                with self.assertRaisesRegex(SnapshotError, 'managed object.*preserved bytes'):
                    snapshot(root / 'source.sqlite', {'vault': vault}, root / 'changed')
                if storage == 'file':
                    (vault / 'object.png').write_bytes(payload)
                else:
                    with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                        db.execute('UPDATE media_upload_intents SET payload=? WHERE object_key=?', (payload, 'object'))
                snapshot(root / 'source.sqlite', {'vault': vault}, root / 'snap')
                restore(root / 'snap', root / 'restored')
                vault.rename(root / 'old-vault')
                if storage == 'file':
                    self.assertEqual((root / 'restored/assets/vault/object.png').read_bytes(), payload)
                else:
                    with closing(sqlite3.connect(root / 'restored/database.sqlite')) as db:
                        self.assertEqual(db.execute('SELECT payload FROM media_upload_intents').fetchone()[0], payload)

    def test_reviewed_alias_is_bound_to_document_owner_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            raw = vault / 'raw/paper'
            raw.mkdir(parents=True)
            shared = vault / 'raw/images'
            shared.mkdir()
            reader = root / 'reader-images'
            reader.mkdir()
            (reader / 'legacy.png').write_bytes(b'\x89PNG\r\n\x1a\nreader')
            body = '![figure](images/legacy.png)'
            image = b'synthetic-shared'
            (raw / 'body.md').write_text(body)
            (shared / 'approved.png').write_bytes(image)
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                self.add_raw(db)
                db.execute('INSERT INTO literature_raws (snapshot_id,item_id,citekey,path,file_sha256,bound_at) VALUES (1,?,?,?,?,?)', ('item','key','raw/paper/body.md',hashlib.sha256(body.encode()).hexdigest(),'now'))
                self.add_file_authority(db)
                self.add_body(db, body, 'imported')
            alias = {'target':'images/legacy.png', 'occurrence_index':0, 'document_source_hash':hashlib.sha256(body.encode()).hexdigest(), 'shared_relative_path':'raw/images/approved.png', 'expected_source_sha256':hashlib.sha256(image).hexdigest(), 'owner_evidence':'synthetic review', 'owner_document_relative_path':'raw/paper/body.md'}
            with self.assertRaisesRegex(SnapshotError, 'alias'):
                snapshot(root / 'source.sqlite', {'vault':vault, 'paper_images':reader}, root / 'missing')
            with self.assertRaisesRegex(SnapshotError, 'evidence invalid'):
                snapshot(root / 'source.sqlite', {'vault':vault, 'paper_images':reader}, root / 'stale', image_aliases=[{**alias, 'document_source_hash':'0' * 64}])
            with self.assertRaisesRegex(SnapshotError, 'evidence invalid'):
                snapshot(root / 'source.sqlite', {'vault':vault, 'paper_images':reader}, root / 'no-owner', image_aliases=[{**alias, 'owner_evidence':''}])
            with self.assertRaisesRegex(SnapshotError, 'hash mismatch'):
                snapshot(root / 'source.sqlite', {'vault':vault, 'paper_images':reader}, root / 'wrong-hash', image_aliases=[{**alias, 'expected_source_sha256':'0' * 64}])
            with self.assertRaisesRegex(SnapshotError, 'alias ambiguous'):
                snapshot(root / 'source.sqlite', {'vault':vault, 'paper_images':reader}, root / 'wrong-owner', image_aliases=[{**alias, 'owner_document_relative_path':'raw/other/body.md'}])
            with self.assertRaisesRegex(SnapshotError, 'alias ambiguous'):
                snapshot(root / 'source.sqlite', {'vault':vault, 'paper_images':reader}, root / 'conflict', image_aliases=[alias, {**alias, 'owner_evidence':'other review'}])
            snapshot(root / 'source.sqlite', {'vault':vault, 'paper_images':reader}, root / 'snap', image_aliases=[alias])
            alias_file = root / 'aliases.json'
            alias_file.write_text(json.dumps([alias]))
            cli = Path(__file__).parents[1] / 'scripts/io_snapshot.py'
            result = subprocess.run([sys.executable, str(cli), 'snapshot', str(root / 'source.sqlite'), str(root / 'cli-snap'), '--root', f'vault={vault}', '--root', f'paper_images={reader}', '--image-aliases', str(alias_file)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            (raw / 'images').mkdir()
            (raw / 'images/legacy.png').write_bytes(b'direct-file')
            snapshot(root / 'source.sqlite', {'vault':vault, 'paper_images':reader}, root / 'direct', image_aliases=[alias])
            self.assertEqual(read_asset(root / 'direct', 'literature_raws', 'path.images/legacy.png', 1), b'direct-file')
            restore(root / 'snap', root / 'out')
            os.rename(vault, root / 'old-vault')
            self.assertEqual(read_asset(root / 'out', 'literature_raws', 'path.images/legacy.png', 1), image)
            self.assertEqual(read_asset(root / 'out', 'literature_raws', 'path.raw_asset:images/legacy.png', 1), b'\x89PNG\r\n\x1a\nreader')

    def test_mapped_document_images_follow_source_inventory_after_relocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            raw = vault / 'raw' / 'paper'
            (raw / 'images').mkdir(parents=True)
            body = '''![reference][figure]
[figure]: images/ref.png
![[images/embed.png|300]]
<img src="images/main.png" srcset="images/small.png 1x, images/large.png 2x">
`![example](images/ignored.png)`
```
![example](images/ignored2.png)
```

    ![indented](images/ignored3.png)

<!-- ![comment](images/ignored4.png) -->
'''
            (raw / 'body.md').write_text(body)
            for name in ('ref.png', 'embed.png', 'main.png', 'small.png', 'large.png'):
                (raw / 'images' / name).write_bytes(b'\x89PNG\r\n\x1a\n' + ('synthetic-' + name).encode())
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                self.add_raw(db)
                db.execute('INSERT INTO literature_raws (snapshot_id,item_id,citekey,path,file_sha256,bound_at) VALUES (1,?,?,?,?,?)', ('item','key','raw/paper/body.md',hashlib.sha256(body.encode()).hexdigest(),'now'))
                self.add_file_authority(db)
                self.add_body(db, body, 'imported')
            snapshot(root / 'source.sqlite', {'vault': vault, 'paper_images': raw / 'images'}, root / 'snap')
            restore(root / 'snap', root / 'out')
            os.rename(vault, root / 'old-vault')
            for name in ('ref.png', 'embed.png', 'main.png', 'small.png', 'large.png'):
                self.assertEqual(read_asset(root / 'out', 'literature_raws', 'path.images/' + name, 1), b'\x89PNG\r\n\x1a\n' + ('synthetic-' + name).encode())
                self.assertEqual(read_asset(root / 'out', 'body_texts', 'text.images/' + name, 1), b'\x89PNG\r\n\x1a\n' + ('synthetic-' + name).encode())

    def test_compressed_source_and_nested_retained_image_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            archive = root / 'archive'
            archive.mkdir()
            body, image = b'<html>synthetic</html>', b'picture'
            (archive / 'source.html.gz').write_bytes(gzip.compress(body))
            (archive / 'figure.png').write_bytes(image)
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                metadata = {'local_images': [{'archive_path': str(archive / 'figure.png'), 'file_hash': hashlib.sha256(image).hexdigest()}]}
                db.execute("INSERT INTO literature_assets (id,item_id,kind,source_path,archive_path,file_hash,metadata_json) VALUES (1,'item','publisher_html',?,?,?,?)", ('old', str(archive / 'source.html.gz'), hashlib.sha256(body).hexdigest(), json.dumps(metadata)))
            snapshot(root / 'source.sqlite', {'vault': vault, 'archive': archive}, root / 'snap')
            (archive / 'figure.png').write_bytes(b'changed')
            with self.assertRaisesRegex(SnapshotError, 'hash mismatch'):
                snapshot(root / 'source.sqlite', {'vault': vault, 'archive': archive}, root / 'bad')

    def test_unsupported_historical_schema_fails_with_version_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                db.execute("UPDATE schema_meta SET value='40' WHERE key='schema_version'")
            with self.assertRaisesRegex(SnapshotError, 'unsupported IO schema version 40'):
                snapshot(root / 'source.sqlite', {'vault': vault}, root / 'snap')
            with closing(sqlite3.connect(root / 'source.sqlite')) as db:
                self.assertEqual(db.execute('SELECT value FROM schema_meta').fetchone(), ('40',))

    def test_populated_retired_body_table_is_reported_and_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                db.executescript("CREATE TABLE raw_texts (id TEXT, text TEXT); INSERT INTO raw_texts VALUES ('legacy','synthetic');")
            with self.assertRaisesRegex(SnapshotError, 'retained legacy table raw_texts'):
                snapshot(root / 'source.sqlite', {'vault': vault}, root / 'snap')
            with closing(sqlite3.connect(root / 'source.sqlite')) as db:
                self.assertEqual(db.execute('SELECT * FROM raw_texts').fetchall(), [('legacy','synthetic')])

    def test_reserved_quarantine_is_recorded_without_inventing_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            staging = root / 'staging'
            staging.mkdir()
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                db.execute("INSERT INTO media_raw_activation_intents (id,item_id,old_mapping_json,old_authority_json,citekey,candidate_hash,state,quarantine_path) VALUES ('intent','item','{}','{}','key',?,'prepared',?)", ('a' * 64, str(staging / 'reserved.md')))
            snapshot(root / 'source.sqlite', {'vault': vault, 'staging': staging}, root / 'snap')
            manifest = json.loads((root / 'snap/manifest.json').read_text())
            reserved = next(x for x in manifest['asset_bindings'] if x['column'] == 'quarantine_path')
            self.assertEqual(reserved['state'], 'reserved')
            restore(root / 'snap', root / 'out')
            with self.assertRaisesRegex(SnapshotError, 'reserved'):
                read_asset(root / 'out', 'media_raw_activation_intents', 'quarantine_path', 'intent')

    def test_body_markup_image_is_resolved_after_source_disappears(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            images = root / 'images'
            images.mkdir()
            (images / 'fig.png').write_bytes(b'\x89PNG\r\n\x1a\nsynthetic')
            body = 'synthetic ![figure](images/fig.png)'
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                self.add_raw(db)
                self.add_body(db, body, 'database')
            with self.assertRaisesRegex(SnapshotError, 'required asset missing'):
                snapshot(root / 'source.sqlite', {'vault': vault}, root / 'missing')
            snapshot(root / 'source.sqlite', {'vault': vault, 'paper_images': images}, root / 'snap')
            restore(root / 'snap', root / 'out')
            os.rename(images, root / 'old-images')
            self.assertEqual(read_asset(root / 'out', 'body_texts', 'text.images/fig.png', 1), b'\x89PNG\r\n\x1a\nsynthetic')

    def test_obsidian_image_without_document_root_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            text = 'synthetic ![[figure.png]]'
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                db.execute("INSERT INTO editor_drafts (id,item_id,created_at) VALUES ('draft','item','now')")
                db.execute("INSERT INTO draft_versions (draft_id,item_id,sha256,characters,authority,stored_at) VALUES ('draft','item',?,?,'database','now')", (hashlib.sha256(text.encode()).hexdigest(),len(text)))
                db.execute('INSERT INTO draft_bodies (draft_id,text) VALUES (?,?)', ('draft', text))
            with self.assertRaisesRegex(SnapshotError, 'image reference has no document root'):
                snapshot(root / 'source.sqlite', {'vault': vault}, root / 'snap')

    def test_recovery_binding_rejects_same_bytes_replaced_inode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                self.add_raw(db)
                db.execute('INSERT INTO private_raw_sources (snapshot_id,item_id,relative_path,sha256,size_bytes) VALUES (1,?,?,?,?)', ('item','body',hashlib.sha256(b'synthetic').hexdigest(),9))
            snapshot(root / 'source.sqlite', {'private_raw': vault}, root / 'snap')
            restore(root / 'snap', root / 'out')
            binding = recovery_binding(root / 'out', 'private_raw_sources', 'relative_path', 1)
            self.assertEqual(read_recovery_asset(root / 'out', 'private_raw_sources', 'relative_path', 1, binding), b'synthetic')
            original = {'staging_path': '/old/path', 'staging_device': 1, 'staging_inode': 2, 'document_hash': binding['sha256'], 'document_bytes': 9}
            adapted = recovery_adapter(root / 'out', 'private_raw_sources', 'relative_path', 1, original)
            self.assertEqual(original['staging_path'], '/old/path')
            fd = os.open(adapted['staging_path'], os.O_RDONLY | os.O_NOFOLLOW)
            try:
                info = os.fstat(fd)
                self.assertEqual((info.st_dev, info.st_ino, info.st_nlink), (adapted['staging_device'], adapted['staging_inode'], 1))
                data = os.read(fd, 1024)
                self.assertEqual((len(data), hashlib.sha256(data).hexdigest()), (adapted['document_bytes'], adapted['document_hash']))
            finally:
                os.close(fd)
            target = Path(binding['path'])
            replacement = target.with_name('replacement')
            replacement.write_bytes(b'synthetic')
            os.replace(replacement, target)
            with self.assertRaisesRegex(SnapshotError, 'identity changed'):
                read_recovery_asset(root / 'out', 'private_raw_sources', 'relative_path', 1, binding)

    def test_overlapping_roles_share_one_tree_and_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            private = vault / 'nested'
            private.mkdir()
            (private / 'raw').write_bytes(b'raw')
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                self.add_raw(db)
                db.execute('INSERT INTO private_raw_sources (snapshot_id,item_id,relative_path,sha256,size_bytes) VALUES (1,?,?,?,?)', ('item','raw',hashlib.sha256(b'raw').hexdigest(),3))
            snapshot(root / 'source.sqlite', {'vault': vault, 'private_raw': private}, root / 'snap')
            restore(root / 'snap', root / 'out')
            os.rename(vault, root / 'old-vault')
            self.assertEqual(read_asset(root / 'out', 'private_raw_sources', 'relative_path', 1), b'raw')
            self.assertEqual(len(list((root / 'out/assets').iterdir())), 1)

    def test_cleanup_backup_manifest_and_versions_are_relocated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            backups = root / 'backups'
            folder = backups / 'batch'
            folder.mkdir(parents=True)
            body = b'backup body'
            (folder / 'body-3.md').write_bytes(body)
            manifest = json.dumps({'bodies': [{'versionId': 3, 'sha256': hashlib.sha256(body).hexdigest()}], 'drafts': []}).encode()
            (folder / 'manifest.json').write_bytes(manifest)
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                db.execute("INSERT INTO literature_cleanup_backups (backup_id,request_id,item_id,path,manifest_sha256,bytes,body_count,draft_count,verified_at,created_at) VALUES ('backup','request','item',?,?,?,1,0,'now','now')", (str(folder), hashlib.sha256(manifest).hexdigest(),len(body)+len(manifest)))
            snapshot(root / 'source.sqlite', {'vault': vault, 'backups': backups}, root / 'snap')
            (folder / 'body-3.md').write_bytes(b'changed original')
            with self.assertRaisesRegex(SnapshotError, 'hash mismatch'):
                snapshot(root / 'source.sqlite', {'vault': vault, 'backups': backups}, root / 'bad')
            restore(root / 'snap', root / 'out')
            os.rename(backups, root / 'old-backups')
            self.assertEqual(read_asset(root / 'out', 'literature_cleanup_backups', 'path.body-3.md', 'backup'), body)
            (root / 'out/assets/backups/batch/body-3.md').write_bytes(b'broken')
            with self.assertRaisesRegex(SnapshotError, 'snapshot integrity mismatch'):
                verify(root / 'out')

    def test_document_staging_and_cleanup_tombstone(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            staging = root / 'staging'
            staging.mkdir()
            body = b'synthetic staged document'
            (staging / 'document').write_bytes(body)
            (staging / 'retired').write_bytes(body)
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                sql = "INSERT INTO media_document_generations (item_id,generation,staging_path,document_hash,document_bytes,state,cleanup_state,staging_device,staging_inode,source_url,metadata_json,provenance_json) VALUES (?,?,?,?,?,?,?,1,1,'','{}','{}')"
                db.execute(sql, ('item', 1, str(staging / 'document'), hashlib.sha256(body).hexdigest(), len(body), 'pending', 'pending'))
                db.execute(sql, ('other', 1, str(staging / 'already-cleaned'), 'old-hash', 1, 'committed', 'cleaned'))
                db.execute(sql, ('retired', 1, str(staging / 'retired'), hashlib.sha256(body).hexdigest(), len(body), 'committed', 'reset-retired'))
            snapshot(root / 'source.sqlite', {'vault': vault, 'staging': staging}, root / 'snap')
            restore(root / 'snap', root / 'out')
            os.rename(staging, root / 'removed-staging')
            self.assertEqual(read_asset(root / 'out', 'media_document_generations', 'staging_path', 1), body)
            self.assertEqual(read_asset(root / 'out', 'media_document_generations', 'staging_path', 3), body)
            with self.assertRaisesRegex(SnapshotError, 'asset reference not uniquely bound'):
                read_asset(root / 'out', 'media_document_generations', 'staging_path', 2)

    def test_unknown_path_and_missing_nested_root_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                db.execute('CREATE TABLE unknown_files (file_path TEXT)')
                db.execute("INSERT INTO unknown_files VALUES ('unknown')")
            with self.assertRaisesRegex(SnapshotError, 'unclassified path'):
                snapshot(root / 'source.sqlite', {'vault': vault}, root / 'snap')
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                db.executescript('DELETE FROM unknown_files; CREATE TABLE mystery (metadata_json TEXT);')
                db.execute('INSERT INTO mystery VALUES (?)', (json.dumps({'nested': {'filePath': '/unknown/file'}}),))
            with self.assertRaisesRegex(SnapshotError, 'unresolved asset root'):
                snapshot(root / 'source.sqlite', {'vault': vault}, root / 'snap')

    def test_relocated_raw_staging_and_quarantine_are_readable_without_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            archive = root / 'archive'
            archive.mkdir()
            stage = root / 'staging'
            stage.mkdir()
            raw, pending, recovery, quarantine = b'raw bytes', b'pending bytes', b'recovery bytes', b'quarantine'
            (archive / 'raw.md').write_bytes(raw)
            (stage / 'pending.png').write_bytes(pending)
            (stage / 'preimage.md').write_bytes(recovery)
            (stage / 'quarantine.md').write_bytes(quarantine)
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                self.add_raw(db, path=str(archive / 'raw.md'))
                db.execute("INSERT INTO media_pending (id,owner_kind,owner_id,source_ref,staging_path,payload_sha256,payload_bytes,created_at) VALUES (1,'item','item','image',?,?,?,'now')", (str(stage / 'pending.png'), hashlib.sha256(pending).hexdigest(), len(pending)))
                preimage = json.dumps({'staging_path': str(stage / 'preimage.md'), 'document_hash': hashlib.sha256(recovery).hexdigest()})
                sql = "INSERT INTO media_raw_activation_intents (id,item_id,old_mapping_json,old_authority_json,citekey,candidate_hash,state,quarantine_path,preimage_json) VALUES (?,'item','{}','{}','key',?,'prepared',?,?)"
                db.execute(sql, ('intent', '', None, preimage))
                db.execute(sql, ('quarantine', hashlib.sha256(quarantine).hexdigest(), str(stage / 'quarantine.md'), None))
                db.execute('CREATE TABLE synthetic_metadata (data_json TEXT)')
                db.execute('INSERT INTO synthetic_metadata VALUES (?)', (json.dumps({'nested': {'asset_path': str(stage / 'preimage.md')}}),))
            snapshot(root / 'source.sqlite', {'vault': vault, 'archive': archive, 'staging': stage}, root / 'snap')
            restore(root / 'snap', root / 'out')
            os.rename(archive, root / 'old-archive')
            os.rename(stage, root / 'old-staging')
            self.assertEqual(read_asset(root / 'out', 'raw_snapshots', 'path', 1), raw)
            self.assertEqual(read_asset(root / 'out', 'media_pending', 'staging_path', 1), pending)
            self.assertEqual(read_asset(root / 'out', 'media_raw_activation_intents', 'preimage_json.staging_path', 'intent'), recovery)
            self.assertEqual(read_asset(root / 'out', 'media_raw_activation_intents', 'quarantine_path', 'quarantine'), quarantine)
            self.assertEqual(read_asset(root / 'out', 'synthetic_metadata', 'data_json.nested.asset_path', 1), recovery)

    def test_private_raw_requires_matching_root_hash_size_and_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = self.make_simple(root)
            private = root / 'private'
            private.mkdir()
            (private / 'raw').write_bytes(b'private synthetic')
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                self.add_raw(db)
                db.execute('INSERT INTO private_raw_sources (snapshot_id,item_id,relative_path,sha256,size_bytes) VALUES (1,?,?,?,?)', ('item','raw',hashlib.sha256(b'private synthetic').hexdigest(),17))
            with self.assertRaisesRegex(SnapshotError, 'required asset missing'):
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
            with self.assertRaisesRegex(SnapshotError, 'unexpected snapshot contents'):
                verify(root / 'out')
            with self.assertRaisesRegex(SnapshotError, 'destination already exists'):
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
                        db.execute("INSERT INTO schema_meta (key,value) VALUES ('synthetic-change','1')")
            with patch('scripts.io_snapshot._backup', side_effect=changing):
                with self.assertRaisesRegex(SnapshotError, 'source changed'):
                    snapshot(root / 'source.sqlite', {'vault': assets}, root / 'snap')
            self.assertFalse((root / 'snap').exists())

    def test_coordinated_database_and_file_changes_do_not_publish(self):
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
                    (assets / 'body').write_bytes(b'new version')
                    with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                        db.execute("INSERT INTO schema_meta (key,value) VALUES ('body-version','new')")
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
            db.executescript((Path(__file__).parent / 'fixtures/io-v41-full.sql').read_text())
            self.assertEqual(db.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone(), (71,))
            db.executescript('''
                INSERT INTO schema_meta (key,value) VALUES ('schema_version','41');
                INSERT INTO items (id, media_type, first_ingested_at, review_date, created_at, updated_at) VALUES ('item','paper','now','now','now','now');
                INSERT INTO item_identities (id,item_id,media_type,identity_type,identity_value,created_at) VALUES (1,'item','paper','doi','synthetic-doi','now');
                INSERT INTO raw_snapshots (id,item_id,path,source_hash,retrieved_at,created_at,provenance) VALUES (1,'item','old-ref','source','now','now','');
                INSERT INTO editor_drafts (id,item_id,raw_snapshot_id,created_at) VALUES ('draft','item',1,'now');
                INSERT INTO literature_files (item_id,citekey,status,source,evidence_json,conditional_writer,enabled_at,updated_at) VALUES ('item','key','active','synthetic','{}','writer','now','now');
                INSERT INTO processing_jobs (id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,intent_json) VALUES ('job','item','edit','once','pending','now','now','now','{"synthetic":true}');
                INSERT INTO ai_feed_settings (freshrss_feed_id,last_seen_at,updated_at) VALUES ('feed','now','now');
                INSERT INTO app_settings (key,value,updated_at) VALUES ('setting','synthetic','now');
                INSERT INTO media_upload_intents (object_key,owner_kind,owner_id,source_ref,object_json,payload,created_at) VALUES ('object','item','item','image','{}',X'0001FF','now');
                INSERT INTO media_receipts (id,owner_kind,owner_id,status,created_at) VALUES (1,'item','item','uploaded','now');
                INSERT INTO media_raw_activation_intents (id,item_id,old_mapping_json,old_authority_json,citekey,candidate_hash,state) VALUES ('intent','item','{}','{}','key','hash','complete');
                CREATE TABLE "future table" (identity TEXT, payload BLOB);
                INSERT INTO "future table" VALUES ('future',X'00FF');
            ''')
            object_digest = hashlib.sha256(b'\x00\x01\xff').hexdigest()
            db.execute("INSERT INTO media_objects (key,namespace,sha256,stored_sha256,ext,bytes,public_url,created_at) VALUES ('object','test',?,?,'png',3,'https://example.invalid/object','now')", (object_digest, object_digest))
            db.execute('INSERT INTO literature_raws (snapshot_id,item_id,citekey,path,file_sha256,bound_at) VALUES (1,?,?,?,?,?)', ('item','key','body.md',hashlib.sha256(body).hexdigest(),'now'))
            db.execute('INSERT INTO literature_drafts (draft_id,item_id,citekey,file_identity,file_draft_id,path,version,payload_sha256,file_sha256,bound_at) VALUES (?,?,?,?,?,?,?,?,?,?)', ('draft','item','key','identity','file-id','draft.md',1,'payload',hashlib.sha256(draft).hexdigest(),'now'))
            db.execute("INSERT INTO body_versions (snapshot_id,item_id,sha256,characters,authority,source,retrieved_at,stored_at) VALUES (1,'item',?, ?, 'imported','synthetic','now','now')", (hashlib.sha256(body).hexdigest(),len(body)))
            db.execute('INSERT INTO body_texts (snapshot_id,text) VALUES (1,?)', (body.decode(),))
            db.execute("INSERT INTO draft_versions (draft_id,item_id,sha256,characters,authority,stored_at,cleaned_at,cleanup_request_id) VALUES ('draft','item',?,?,'imported','now',NULL,NULL)", (hashlib.sha256(draft).hexdigest(),len(draft)))
            db.execute('INSERT INTO draft_bodies (draft_id,text) VALUES (?,?)', ('draft',draft.decode()))
            db.commit()
            snapshot(root / 'source.sqlite', {'vault': vault}, root / 'snap')
            report = verify(root / 'snap')
            self.assertEqual(report['remote_reference_counts'], {'media_objects': 1, 'media_receipts': 1, 'media_upload_intents': 1})
            remote = remote_references(root / 'snap')
            self.assertEqual(remote, [{'key': 'object', 'namespace': 'test', 'expected_sha256': object_digest, 'status': 'requires_live_readback'}])
            coverage = json.loads((root / 'snap/manifest.json').read_text())['reference_coverage']
            self.assertIn(['literature_cleanup_backups', 'path', 'bound'], coverage)
            self.assertIn(['media_document_generations', 'provenance_json', 'recursive_path_keys'], coverage)
            restore(root / 'snap', root / 'out')
            with closing(sqlite3.connect(root / 'out/database.sqlite')) as result:
                schema = db.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
                self.assertEqual(schema, result.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall())
                for name, _ in schema:
                    quoted = '"' + name.replace('"', '""') + '"'
                    self.assertCountEqual(db.execute('SELECT * FROM ' + quoted).fetchall(), result.execute('SELECT * FROM ' + quoted).fetchall(), name)
                self.assertEqual(result.execute('SELECT authority FROM body_versions').fetchone(), ('imported',))
                self.assertEqual(result.execute('SELECT artifact_hash FROM editor_drafts').fetchone(), (None,))
                self.assertEqual(result.execute('SELECT identity_value FROM item_identities').fetchone(), ('synthetic-doi',))
                self.assertEqual(result.execute('SELECT intent_json FROM processing_jobs').fetchone(), ('{"synthetic":true}',))
                self.assertEqual(result.execute('SELECT payload FROM media_upload_intents').fetchone(), (b'\x00\x01\xff',))
                self.assertEqual(result.execute('SELECT payload FROM "future table"').fetchone(), (b'\x00\xff',))
            db.close()
            self.assertEqual((root / 'out/assets/vault/draft.md').read_bytes(), draft)
            with closing(sqlite3.connect(root / 'source.sqlite')) as changed, changed:
                changed.execute("INSERT INTO items (id, media_type, first_ingested_at, review_date, created_at, updated_at) VALUES ('other','paper','now','now','now','now')")
                changed.execute("UPDATE body_versions SET item_id='other' WHERE snapshot_id=1")
            with self.assertRaisesRegex(SnapshotError, 'body version identity mismatch'):
                snapshot(root / 'source.sqlite', {'vault': vault}, root / 'mismatch')

    def make_simple(self, root):
        assets = root / 'vault'
        assets.mkdir()
        (assets / 'body').write_bytes(b'synthetic')
        db = sqlite3.connect(root / 'source.sqlite')
        self.init_schema(db)
        db.commit()
        db.close()
        return assets

    def test_tampering_and_existing_destination_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = self.make_simple(root)
            snapshot(root / 'source.sqlite', {'vault': assets}, root / 'snap')
            restore(root / 'snap', root / 'out')
            with self.assertRaisesRegex(SnapshotError, 'destination already exists'):
                restore(root / 'snap', root / 'out')
            (root / 'snap/assets/vault/body').write_bytes(b'altered')
            with self.assertRaisesRegex(SnapshotError, 'snapshot integrity mismatch'):
                verify(root / 'snap')
            with self.assertRaisesRegex(SnapshotError, 'snapshot integrity mismatch'):
                restore(root / 'snap', root / 'new')
            self.assertFalse((root / 'new').exists())
            self.assertEqual((root / 'out/assets/vault/body').read_bytes(), b'synthetic')

    def test_missing_changed_and_unsafe_references_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = self.make_simple(root)
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                self.add_raw(db)
                db.execute('INSERT INTO literature_raws (snapshot_id,item_id,citekey,path,file_sha256,bound_at) VALUES (1, ?, ?, ?, ?, ?)', ('item', 'key', '../outside', hashlib.sha256(b'synthetic').hexdigest(), 'now'))
                self.add_file_authority(db)
            with self.assertRaisesRegex(SnapshotError, 'unsafe asset reference'):
                snapshot(root / 'source.sqlite', {'vault': assets}, root / 'snap')
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                db.execute("UPDATE literature_raws SET path='body', file_sha256='wrong'")
            with self.assertRaisesRegex(SnapshotError, 'required asset hash mismatch'):
                snapshot(root / 'source.sqlite', {'vault': assets}, root / 'snap')
            self.assertFalse((root / 'snap').exists())

    def test_symlinks_and_interrupted_destination_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = self.make_simple(root)
            (assets / 'link').symlink_to(root / 'source.sqlite')
            with self.assertRaisesRegex(SnapshotError, 'asset tree contains an unsafe entry'):
                snapshot(root / 'source.sqlite', {'vault': assets}, root / 'snap')
            (assets / 'link').unlink()
            snapshot(root / 'source.sqlite', {'vault': assets}, root / 'snap')
            (root / 'interrupted').mkdir()
            (root / 'interrupted/partial').write_text('keep')
            with self.assertRaisesRegex(SnapshotError, 'destination already exists'):
                restore(root / 'snap', root / 'interrupted')
            self.assertEqual((root / 'interrupted/partial').read_text(), 'keep')
            (root / 'snap/assets/vault/body').unlink()
            (root / 'snap/assets/vault/body').symlink_to(root / 'source.sqlite')
            with self.assertRaisesRegex(SnapshotError, 'asset tree contains an unsafe entry'):
                restore(root / 'snap', root / 'other')

    def test_unknown_raw_and_pending_media_are_not_silently_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = self.make_simple(root)
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                self.add_raw(db, path='old')
            with self.assertRaisesRegex(SnapshotError, 'unresolved asset root'):
                snapshot(root / 'source.sqlite', {'vault': assets}, root / 'snap')
            with closing(sqlite3.connect(root / 'source.sqlite')) as db, db:
                db.execute('DELETE FROM raw_snapshots')
                db.execute("INSERT INTO media_pending (id,owner_kind,owner_id,source_ref,staging_path,created_at) VALUES (1,'item','item','image','unknown','now')")
            with self.assertRaisesRegex(SnapshotError, 'media staging has no immutable byte evidence'):
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
            self.init_schema(db)
            db.executescript('''
                CREATE TABLE future_table (id TEXT PRIMARY KEY, payload BLOB);
                INSERT INTO items (id,media_type,first_ingested_at,review_date,created_at,updated_at) VALUES ('synthetic-item','paper','now','now','now','now');
                INSERT INTO raw_snapshots (id,item_id,path,source_hash,retrieved_at,created_at) VALUES (1,'synthetic-item','','source','now','now');
                INSERT INTO future_table VALUES ('opaque', X'000102FF');
            ''')
            db.execute('INSERT INTO literature_raws (snapshot_id,item_id,citekey,path,file_sha256,bound_at) VALUES (1, ?, ?, ?, ?, ?)', ('synthetic-item', 'key', 'raw/body.md', hashlib.sha256(body).hexdigest(), 'now'))
            self.add_file_authority(db, 'synthetic-item')
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
