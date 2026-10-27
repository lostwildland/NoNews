"""Conservative IO snapshot utility. See docs/acceptance/t01-snapshot-investigation.md."""
import argparse
from contextlib import closing
import hashlib
import json
import os
import re
import sqlite3
import stat
import tempfile
import time
from pathlib import Path
from urllib.parse import quote


class SnapshotError(Exception):
    """Snapshot cannot be proven safe or complete."""


PATH_FIELDS = {
    ('literature_raws','path'), ('literature_drafts','path'), ('private_raw_sources','relative_path'),
    ('media_pending','staging_path'), ('media_document_generations','staging_path'),
    ('raw_snapshots','path'), ('media_raw_activation_intents','quarantine_path'),
    ('literature_assets','archive_path'), ('literature_assets','source_path'), ('ingestion_failures','artifact_path'),
    ('literature_cleanup_backups','path'),
    ('literature_reading_notes','path'), ('news_notes','path'),
    ('literature_cleanup_legacy_media_recovery','path'),
}
HISTORICAL_PATH_FIELDS = {('legacy_content_imports', 'path')}


def _hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _inventory(root, copy_to=None):
    result = {}
    if root.is_symlink() or not root.is_dir():
        raise SnapshotError('asset root is missing or unsafe')
    if copy_to is not None:
        copy_to.mkdir(parents=True)
    def walk(fd, prefix):
        with os.scandir(fd) as entries:
            names = [entry.name for entry in entries]
        for name in names:
            rel = prefix + name
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            try:
                child = os.open(name, flags, dir_fd=fd)
            except OSError as exc:
                raise SnapshotError('asset tree contains an unsafe entry') from exc
            try:
                mode = os.fstat(child).st_mode
                if stat.S_ISDIR(mode):
                    result[rel] = None
                    if copy_to is not None:
                        (copy_to / rel).mkdir()
                    walk(child, rel + '/')
                elif stat.S_ISREG(mode):
                    h = hashlib.sha256()
                    size = 0
                    with os.fdopen(os.dup(child), 'rb') as src:
                        if copy_to is None:
                            for block in iter(lambda: src.read(1024 * 1024), b''):
                                h.update(block)
                                size += len(block)
                        else:
                            with open(copy_to / rel, 'xb') as dst:
                                for block in iter(lambda: src.read(1024 * 1024), b''):
                                    h.update(block)
                                    size += len(block)
                                    dst.write(block)
                    result[rel] = {'sha256': h.hexdigest(), 'size': size}
                else:
                    raise SnapshotError('asset tree contains an unsafe entry')
            finally:
                os.close(child)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        walk(fd, '')
    finally:
        os.close(fd)
    return result


def _read_file(root, relative):
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parts = relative.split('/')
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        child = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            if not stat.S_ISREG(os.fstat(child).st_mode):
                raise SnapshotError('unsafe asset')
            with os.fdopen(os.dup(child), 'rb') as source:
                return source.read()
        finally:
            os.close(child)
    finally:
        os.close(fd)


def _db(path):
    return sqlite3.connect('file:' + quote(str(path.resolve()), safe='/') + '?mode=ro', uri=True)


def _backup(source, target):
    deadline = time.monotonic() + 10
    def progress(status, remaining, total):
        if time.monotonic() > deadline:
            raise SnapshotError('database writers prevented a bounded backup')
    with closing(_db(source)) as src, closing(sqlite3.connect(target)) as dst:
        src.backup(dst, pages=256, progress=progress, sleep=0.05)
        dst.execute('PRAGMA journal_mode=DELETE')


def _database(path):
    with closing(_db(path)) as db:
        if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise SnapshotError('database integrity check failed')
        if db.execute('PRAGMA foreign_key_check').fetchone():
            raise SnapshotError('database foreign key check failed')
        objects = db.execute("SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name").fetchall()
        tables = {}
        for kind, name, _, _ in objects:
            if kind != 'table':
                continue
            ident = '"' + name.replace('"', '""') + '"'
            rows = db.execute('SELECT * FROM ' + ident)
            hashes = []
            for row in rows:
                encoded = []
                for value in row:
                    if isinstance(value, bytes):
                        encoded.append(['blob', value.hex()])
                    else:
                        encoded.append([type(value).__name__, value])
                hashes.append(hashlib.sha256(json.dumps(encoded, ensure_ascii=True, allow_nan=False, separators=(',', ':')).encode()).hexdigest())
            tables[name] = {'count': len(hashes), 'sha256': hashlib.sha256(''.join(sorted(hashes)).encode()).hexdigest()}
        schema_hash = hashlib.sha256(json.dumps(objects, ensure_ascii=True, separators=(',', ':')).encode()).hexdigest()
        try:
            version = db.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
        except sqlite3.Error:
            version = None
        return {'schema_sha256': schema_hash, 'tables': tables, 'schema_version': version[0] if version else None,
                'user_version': db.execute('PRAGMA user_version').fetchone()[0],
                'application_id': db.execute('PRAGMA application_id').fetchone()[0]}


def _asset_bindings(path, assets, roots, asset_dirs):
    """Bind recognized operational file references without rewriting source rows."""
    bindings = []
    def bind(table, column, identity, value, expected=None, size=None, relative_root=None):
        if not isinstance(value, str) or not value or '\x00' in value or '\\' in value:
            raise SnapshotError('invalid required asset reference')
        if relative_root and not Path(value).is_absolute():
            root, relative = relative_root, value
        else:
            p = Path(value)
            if not p.is_absolute() or any(part in ('.', '..') for part in value.split('/')):
                raise SnapshotError('unresolved asset root')
            matches = [(name, p.relative_to(base).as_posix()) for name, base in roots.items() if p.is_relative_to(base) and p != base]
            if len(matches) != 1:
                raise SnapshotError('unresolved asset root')
            root, relative = matches[0]
        if any(part in ('', '.', '..') for part in relative.split('/')):
            raise SnapshotError('unsafe asset reference')
        evidence = assets.get(root, {}).get(relative)
        if not isinstance(evidence, dict):
            raise SnapshotError('required asset missing')
        if expected and evidence['sha256'] != expected:
            raise SnapshotError('required asset hash mismatch')
        if size is not None and evidence['size'] != size:
            raise SnapshotError('required asset size mismatch')
        bindings.append({'table': table, 'column': column, 'id': identity, 'root': root, 'path': relative, 'sha256': evidence['sha256']})
    with closing(_db(path)) as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table, identity, column, digest, size, root in (
            ('literature_raws', 'snapshot_id', 'path', 'file_sha256', None, 'vault'),
            ('literature_drafts', 'draft_id', 'path', 'file_sha256', None, 'vault'),
            ('private_raw_sources', 'snapshot_id', 'relative_path', 'sha256', 'size_bytes', 'private_raw'),
            ('media_pending', 'id', 'staging_path', 'payload_sha256', 'payload_bytes', None),
        ):
            if table not in tables:
                continue
            cols = {r[1] for r in db.execute(f'PRAGMA table_info("{table}")')}
            if not {column, digest} <= cols or (size and size not in cols):
                if db.execute(f'SELECT 1 FROM "{table}" LIMIT 1').fetchone():
                    raise SnapshotError('unsupported asset reference schema')
                continue
            for row in db.execute(f'SELECT "{identity}", "{column}", "{digest}"' + (f', "{size}"' if size else ', NULL') + f' FROM "{table}"'):
                if table == 'media_pending' and (not row[2] or row[3] is None):
                    raise SnapshotError('media staging has no immutable byte evidence')
                bind(table, column, row[0], row[1], row[2], row[3], root)
        if 'media_document_generations' in tables:
            for ident, value, digest, size, state, cleanup in db.execute('SELECT rowid, staging_path, document_hash, document_bytes, state, cleanup_state FROM media_document_generations'):
                if state == 'committed' and cleanup in ('cleaned', 'reset-retired'):
                    continue
                if not digest:
                    raise SnapshotError('document staging has no immutable byte evidence')
                bind('media_document_generations', 'staging_path', ident, value, digest, size)
        for table, identity, column, digest, relative_root in (
            ('literature_assets', 'id', 'archive_path', 'file_hash', None),
            ('ingestion_failures', 'id', 'artifact_path', None, None),
            ('literature_reading_notes', 'item_id', 'path', None, 'vault'),
            ('news_notes', 'item_id', 'path', None, 'vault'),
            ('literature_cleanup_legacy_media_recovery', 'rowid', 'path', None, None),
        ):
            if table not in tables:
                continue
            cols = {r[1] for r in db.execute(f'PRAGMA table_info("{table}")')}
            if column not in cols or (digest and digest not in cols):
                raise SnapshotError('unsupported asset reference schema')
            query = f'SELECT "{identity}", "{column}", ' + (f'"{digest}"' if digest else 'NULL') + f' FROM "{table}"'
            for ident, value, expected in db.execute(query):
                if value:
                    bind(table, column, ident, value, expected, relative_root=relative_root)
        if 'literature_assets' in tables:
            for ident, source, archive, digest in db.execute('SELECT id, source_path, archive_path, file_hash FROM literature_assets'):
                if not archive:
                    bind('literature_assets', 'source_path', ident, source, digest)
        if 'literature_cleanup_backups' in tables:
            for ident, directory, digest, body_count, draft_count in db.execute('SELECT backup_id, path, manifest_sha256, body_count, draft_count FROM literature_cleanup_backups'):
                manifest_path = str(Path(directory) / 'manifest.json')
                bind('literature_cleanup_backups', 'path.manifest.json', ident, manifest_path, digest)
                binding = bindings[-1]
                try:
                    manifest_bytes = _read_file(asset_dirs[binding['root']], binding['path'])
                    if hashlib.sha256(manifest_bytes).hexdigest() != digest:
                        raise SnapshotError('cleanup manifest hash mismatch')
                    backup = json.loads(manifest_bytes)
                    if len(backup['bodies']) != body_count or len(backup['drafts']) != draft_count:
                        raise SnapshotError('cleanup manifest count mismatch')
                    for group, prefix, key in ((backup['bodies'], 'body-', 'versionId'), (backup['drafts'], 'draft-', 'draftId')):
                        for record in group:
                            name = prefix + str(record[key]) + '.md'
                            if '/' in name or '\\' in name:
                                raise SnapshotError('unsafe cleanup backup name')
                            bind('literature_cleanup_backups', 'path.' + name, ident, str(Path(directory) / name), record['sha256'])
                except (OSError, ValueError, TypeError, KeyError) as exc:
                    raise SnapshotError('invalid cleanup backup') from exc
        if 'raw_snapshots' in tables:
            for ident, value in db.execute('SELECT id, path FROM raw_snapshots'):
                mapped = 'literature_raws' in tables and db.execute('SELECT 1 FROM literature_raws WHERE snapshot_id=?', (ident,)).fetchone()
                private = 'private_raw_sources' in tables and db.execute('SELECT 1 FROM private_raw_sources WHERE snapshot_id=?', (ident,)).fetchone()
                stored = 'body_versions' in tables and db.execute("SELECT 1 FROM body_versions WHERE snapshot_id=? AND authority='database'", (ident,)).fetchone()
                if not (mapped or private or stored):
                    bind('raw_snapshots', 'path', ident, value)
        if 'media_raw_activation_intents' in tables:
            columns = {r[1] for r in db.execute('PRAGMA table_info(media_raw_activation_intents)')}
            if {'id', 'preimage_json', 'quarantine_path', 'candidate_hash'} <= columns:
                for ident, preimage, quarantine, candidate in db.execute('SELECT id, preimage_json, quarantine_path, candidate_hash FROM media_raw_activation_intents'):
                    if quarantine:
                        if not candidate:
                            raise SnapshotError('quarantine has no immutable byte evidence')
                        bind('media_raw_activation_intents', 'quarantine_path', ident, quarantine, candidate)
                    if preimage:
                        try:
                            data = json.loads(preimage)
                            bind('media_raw_activation_intents', 'preimage_json.staging_path', ident, data['staging_path'], data['document_hash'])
                        except (ValueError, TypeError, KeyError) as exc:
                            raise SnapshotError('invalid recovery preimage') from exc
        for table in tables:
            ident = '"' + table.replace('"', '""') + '"'
            for column in db.execute(f'PRAGMA table_info({ident})'):
                name = column[1]
                if ('path' in name.lower() or name.lower().endswith('_root')) and (table, name) not in PATH_FIELDS | HISTORICAL_PATH_FIELDS:
                    col = '"' + name.replace('"', '""') + '"'
                    if db.execute(f'SELECT 1 FROM {ident} WHERE {col} IS NOT NULL AND {col} != \'\' LIMIT 1').fetchone():
                        raise SnapshotError('unclassified path-bearing field')
                if name.lower().endswith('_json'):
                    col = '"' + name.replace('"', '""') + '"'
                    for rowid, raw in db.execute(f'SELECT rowid, {col} FROM {ident} WHERE {col} IS NOT NULL AND {col} != \'\''):
                        try:
                            value = json.loads(raw)
                        except (ValueError, TypeError) as exc:
                            raise SnapshotError('unreadable JSON reference metadata') from exc
                        def visit(obj, trail):
                            if isinstance(obj, dict):
                                for key, nested in obj.items():
                                    key_path = trail + '.' + key
                                    if isinstance(nested, str) and nested and (key.lower() == 'root' or key.lower().endswith('_root')):
                                        if Path(nested) not in roots.values():
                                            raise SnapshotError('unresolved root in JSON metadata')
                                    elif isinstance(nested, str) and nested and (key.lower() == 'path' or key.lower().endswith('_path') or key.lower().endswith('path')):
                                        if table == 'media_raw_activation_intents' and key_path == 'preimage_json.staging_path':
                                            continue
                                        bind(table, key_path, rowid, nested, relative_root='vault' if name in ('old_mapping_json', 'old_authority_json') else None)
                                    else:
                                        visit(nested, key_path)
                            elif isinstance(obj, list):
                                for index, nested in enumerate(obj):
                                    visit(nested, trail + f'[{index}]')
                        visit(value, name)
    ordered = sorted(bindings, key=lambda x: (x['table'], x['column'], str(x['id'])))
    identities = [(b['table'], b['column'], b['id']) for b in ordered]
    if len(set(identities)) != len(identities):
        raise SnapshotError('duplicate asset identity')
    return ordered


def _coverage(path):
    fields = []
    with closing(_db(path)) as db:
        for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            ident = '"' + table.replace('"', '""') + '"'
            for column in db.execute(f'PRAGMA table_info({ident})'):
                name = column[1]
                if 'path' in name.lower() or name.lower().endswith('_root'):
                    classification = ('bound' if (table, name) in PATH_FIELDS else
                                      'historical' if (table, name) in HISTORICAL_PATH_FIELDS else 'reject_if_populated')
                    fields.append([table, name, classification])
                if name.lower().endswith('_json'):
                    fields.append([table, name, 'recursive_path_keys'])
    return fields


def _references(path, assets, bindings):
    """Validate known file authorities; reject unsupported live references."""
    with closing(_db(path)) as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table, root, path_col, hash_col in (
            ('literature_raws', 'vault', 'path', 'file_sha256'),
            ('literature_drafts', 'vault', 'path', 'file_sha256'),
            ('private_raw_sources', 'private_raw', 'relative_path', 'sha256'),
        ):
            if table not in tables:
                continue
            for relative, expected in db.execute(f'SELECT "{path_col}", "{hash_col}" FROM "{table}"'):
                if not isinstance(relative, str) or not relative or '\\' in relative:
                    raise SnapshotError('invalid file reference')
                p = Path(relative)
                if p.is_absolute() or any(x in ('', '.', '..') for x in relative.split('/')):
                    raise SnapshotError('unsafe file reference')
                file_evidence = assets.get(root, {}).get(relative)
                if not isinstance(file_evidence, dict) or file_evidence.get('sha256') != expected:
                    raise SnapshotError('file reference missing or changed')
        if 'private_raw_sources' in tables:
            for relative, size in db.execute('SELECT relative_path, size_bytes FROM private_raw_sources'):
                if assets['private_raw'][relative]['size'] != size:
                    raise SnapshotError('private raw size mismatch')
        # Unmapped Raw may refer to an artifact, a missing body, or a tombstone.
        if 'raw_snapshots' in tables:
            cols = {r[1] for r in db.execute('PRAGMA table_info(raw_snapshots)')}
            if {'id', 'path'} <= cols:
                for ident, path_value in db.execute('SELECT id, path FROM raw_snapshots'):
                    mapped = 'literature_raws' in tables and db.execute('SELECT 1 FROM literature_raws WHERE snapshot_id=?', (ident,)).fetchone()
                    private = 'private_raw_sources' in tables and db.execute('SELECT 1 FROM private_raw_sources WHERE snapshot_id=?', (ident,)).fetchone()
                    stored = 'body_versions' in tables and db.execute("SELECT 1 FROM body_versions WHERE snapshot_id=? AND authority='database'", (ident,)).fetchone()
                    bound = any(b['table'] == 'raw_snapshots' and b['id'] == ident for b in bindings)
                    if not (mapped or private or stored or bound):
                        raise SnapshotError('unresolved raw authority or artifact reference')
        for table in ('literature_raws', 'private_raw_sources'):
            if table in tables and 'raw_snapshots' in tables:
                if db.execute(f'SELECT 1 FROM "{table}" x JOIN raw_snapshots r ON r.id=x.snapshot_id WHERE x.item_id != r.item_id LIMIT 1').fetchone():
                    raise SnapshotError('raw reference identity mismatch')
        if {'body_versions', 'raw_snapshots'} <= tables:
            if db.execute('SELECT 1 FROM body_versions v JOIN raw_snapshots r ON r.id=v.snapshot_id WHERE v.item_id != r.item_id LIMIT 1').fetchone():
                raise SnapshotError('body version identity mismatch')
        for versions, texts, key in (('body_versions', 'body_texts', 'snapshot_id'),
                                     ('draft_versions', 'draft_bodies', 'draft_id')):
            if versions in tables and texts in tables:
                query = f'SELECT v.sha256, v.cleaned_at, t.text FROM "{versions}" v LEFT JOIN "{texts}" t ON v."{key}"=t."{key}"'
                for digest, cleaned, body in db.execute(query):
                    if body is None:
                        if cleaned is None:
                            raise SnapshotError('version text missing without cleanup evidence')
                    elif hashlib.sha256(body.encode('utf-8')).hexdigest() != digest:
                        raise SnapshotError('version text hash mismatch')
        if 'editor_drafts' in tables:
            for ident, item in db.execute('SELECT id, item_id FROM editor_drafts'):
                mapping = db.execute('SELECT item_id FROM literature_drafts WHERE draft_id=?', (ident,)).fetchone() if 'literature_drafts' in tables else None
                version = db.execute('SELECT item_id FROM draft_versions WHERE draft_id=?', (ident,)).fetchone() if 'draft_versions' in tables else None
                if not (mapping or version):
                    raise SnapshotError('unresolved draft authority')
                if any(row and row[0] != item for row in (mapping, version)):
                    raise SnapshotError('draft reference identity mismatch')
        if 'literature_files' in tables and 'literature_raws' in tables:
            if db.execute('SELECT 1 FROM literature_files f LEFT JOIN literature_raws r ON r.item_id=f.item_id WHERE r.item_id IS NULL LIMIT 1').fetchone():
                raise SnapshotError('unresolved literature file authority')
            if db.execute('SELECT 1 FROM literature_raws r JOIN literature_files f ON f.item_id=r.item_id WHERE r.citekey != f.citekey LIMIT 1').fetchone():
                raise SnapshotError('literature reference identity mismatch')
            if 'literature_drafts' in tables and db.execute('SELECT 1 FROM literature_drafts d JOIN literature_files f ON f.item_id=d.item_id WHERE d.citekey != f.citekey LIMIT 1').fetchone():
                raise SnapshotError('literature draft identity mismatch')
        return {table: db.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
                for table in ('media_objects', 'media_receipts', 'media_upload_intents') if table in tables}


def _publish(staging, destination):
    parent = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        try:
            os.mkdir(destination.name, mode=0o700, dir_fd=parent)
        except FileExistsError as exc:
            raise SnapshotError('destination already exists') from exc
        dest_fd = os.open(destination.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        stage_fd = os.open(staging, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for entry in staging.iterdir():
                os.rename(entry.name, entry.name, src_dir_fd=stage_fd, dst_dir_fd=dest_fd)
        finally:
            os.close(stage_fd)
            os.close(dest_fd)
    finally:
        os.close(parent)


def _check_destination(destination, sources):
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise SnapshotError('destination already exists')
    if not destination.parent.is_dir() or destination.parent.is_symlink():
        raise SnapshotError('destination parent is missing or unsafe')
    resolved = destination.resolve()
    for source in sources:
        src = Path(source).resolve()
        if resolved == src or src in resolved.parents or resolved in src.parents:
            raise SnapshotError('destination overlaps a source')
    return destination


def snapshot(database, roots, destination):
    database = Path(database)
    if database.is_symlink() or not database.is_file():
        raise SnapshotError('source database is missing or unsafe')
    if not roots or any(not re.fullmatch(r'[a-z][a-z0-9_]*', name) for name in roots):
        raise SnapshotError('explicit named asset roots required')
    roots = {name: Path(path) for name, path in roots.items()}
    sources = [database.resolve(), *(p.resolve() for p in roots.values())]
    if any(a == b or a in b.parents or b in a.parents for i, a in enumerate(sources) for b in sources[i + 1:]):
        raise SnapshotError('source roots overlap')
    destination = _check_destination(destination, [database, *roots.values()])
    with tempfile.TemporaryDirectory(prefix='.io-snapshot-', dir=destination.parent) as temp:
        stage = Path(temp)
        first = {name: _inventory(path) for name, path in roots.items()}
        _backup(database, stage / 'database.sqlite')
        evidence = _database(stage / 'database.sqlite')
        root_bindings = {name: str(path.absolute()) for name, path in roots.items()}
        bindings = _asset_bindings(stage / 'database.sqlite', first, {name: Path(path) for name, path in root_bindings.items()}, roots)
        references = _references(stage / 'database.sqlite', first, bindings)
        copied = {name: _inventory(root, stage / 'assets' / name) for name, root in roots.items()}
        second = {name: _inventory(path) for name, path in roots.items()}
        _backup(database, stage / 'check.sqlite')
        if first != copied or first != second or evidence != _database(stage / 'check.sqlite'):
            raise SnapshotError('source changed during snapshot; retry after writers pause')
        (stage / 'check.sqlite').unlink()
        manifest = {'format': 2, 'database_sha256': _hash(stage / 'database.sqlite'), 'database': evidence, 'assets': first, 'remote_reference_counts': references, 'source_roots': root_bindings, 'asset_bindings': bindings, 'reference_coverage': _coverage(stage / 'database.sqlite')}
        (stage / 'manifest.json').write_text(json.dumps(manifest, sort_keys=True), encoding='utf-8')
        verify(stage)
        _publish(stage, destination)


def verify(directory):
    root = Path(directory)
    try:
        inventory = _inventory(root)
        if set(p.split('/')[0] for p in inventory) != {'database.sqlite', 'manifest.json', 'assets'}:
            raise SnapshotError('unexpected snapshot contents')
        manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
        if set(manifest) != {'format', 'database_sha256', 'database', 'assets', 'remote_reference_counts', 'source_roots', 'asset_bindings', 'reference_coverage'} or manifest['format'] != 2:
            raise SnapshotError('invalid manifest')
        if not isinstance(manifest['assets'], dict) or not manifest['assets']:
            raise SnapshotError('invalid asset roots')
        names = manifest['assets'].keys()
        if any(not isinstance(n, str) or not re.fullmatch(r'[a-z][a-z0-9_]*', n) for n in names):
            raise SnapshotError('invalid asset root name')
        if {p.name for p in (root / 'assets').iterdir()} != set(names):
            raise SnapshotError('asset roots differ')
        source_roots = manifest['source_roots']
        if not isinstance(source_roots, dict) or set(source_roots) != set(names) or any(not isinstance(p, str) or not Path(p).is_absolute() or '..' in Path(p).parts for p in source_roots.values()):
            raise SnapshotError('invalid source root bindings')
        assets = {n: _inventory(root / 'assets' / n) for n in names}
        if assets != manifest['assets'] or _hash(root / 'database.sqlite') != manifest['database_sha256'] or _database(root / 'database.sqlite') != manifest['database']:
            raise SnapshotError('snapshot integrity mismatch')
        bindings = _asset_bindings(root / 'database.sqlite', assets, {n: Path(p) for n, p in source_roots.items()}, {n: root / 'assets' / n for n in names})
        if bindings != manifest['asset_bindings'] or _coverage(root / 'database.sqlite') != manifest['reference_coverage'] or _references(root / 'database.sqlite', assets, bindings) != manifest['remote_reference_counts']:
            raise SnapshotError('reference evidence mismatch')
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error) as exc:
        raise SnapshotError('invalid or unreadable snapshot') from exc
    return {'integrity_verified': True, 'coverage': 'incomplete', 'tables': len(manifest['database']['tables']), 'asset_roots': len(assets), 'remote_reference_counts': manifest['remote_reference_counts']}


def read_asset(directory, table, column, identity):
    """Read a recognized reference from the relocated tree after full validation."""
    root = Path(directory)
    verify(root)
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    matches = [b for b in manifest['asset_bindings'] if b['table'] == table and b['column'] == column and b['id'] == identity]
    if len(matches) != 1:
        raise SnapshotError('asset reference not uniquely bound')
    binding = matches[0]
    data = _read_file(root / 'assets' / binding['root'], binding['path'])
    if hashlib.sha256(data).hexdigest() != binding['sha256']:
        raise SnapshotError('asset changed during read')
    return data


def restore(source, destination):
    source = Path(source)
    destination = _check_destination(destination, [source])
    verify(source)
    with tempfile.TemporaryDirectory(prefix='.io-restore-', dir=destination.parent) as temp:
        stage = Path(temp)
        _inventory(source, stage / 'copy')
        verify(stage / 'copy')
        _publish(stage / 'copy', destination)


def main():
    parser = argparse.ArgumentParser(description='Create, verify, or restore a conservative IO snapshot')
    sub = parser.add_subparsers(dest='command', required=True)
    make = sub.add_parser('snapshot')
    make.add_argument('database')
    make.add_argument('destination')
    make.add_argument('--root', action='append', required=True, metavar='NAME=PATH')
    check = sub.add_parser('verify')
    check.add_argument('snapshot')
    recover = sub.add_parser('restore')
    recover.add_argument('snapshot')
    recover.add_argument('destination')
    args = parser.parse_args()
    try:
        if args.command == 'snapshot':
            roots = {}
            for value in args.root:
                name, sep, path = value.partition('=')
                if not sep or name in roots or not path:
                    raise SnapshotError('invalid or duplicate root')
                roots[name] = path
            snapshot(args.database, roots, args.destination)
        elif args.command == 'verify':
            print(json.dumps(verify(args.snapshot), sort_keys=True))
            return 0
        else:
            restore(args.snapshot, args.destination)
        print('OK (limited coverage; see T01 acceptance notes)')
    except (SnapshotError, OSError, sqlite3.Error) as exc:
        print('Snapshot refused: ' + (str(exc) if isinstance(exc, SnapshotError) else 'filesystem or database error'))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
