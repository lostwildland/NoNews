"""Conservative IO snapshot utility. See docs/acceptance/t01-snapshot-investigation.md."""
import argparse
from contextlib import closing
import hashlib
import gzip
import io
import json
import os
import posixpath
import re
import sqlite3
import stat
import struct
import tempfile
import time
import zlib
from pathlib import Path
from urllib.parse import quote
from urllib.parse import unquote, urlsplit

if __package__:
    from .io_image_inventory import inventory_markdown_images
else:
    from io_image_inventory import inventory_markdown_images


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


def _read_file_identity(root, relative):
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parts = relative.split('/')
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        child = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            info = os.fstat(child)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise SnapshotError('unsafe asset')
            with os.fdopen(os.dup(child), 'rb') as source:
                data = source.read()
            after = os.fstat(child)
            if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
                raise SnapshotError('asset changed during read')
            return data, info
        finally:
            os.close(child)
    finally:
        os.close(fd)


def _read_file(root, relative):
    return _read_file_identity(root, relative)[0]


def _db(path):
    return sqlite3.connect('file:' + quote(str(path.resolve()), safe='/') + '?mode=ro', uri=True)


def _source_files(source, copy_to=None):
    """Observe database sidecars without ever opening the source with SQLite."""
    parent = os.open(source.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    result = {}
    try:
        for suffix in ('', '-wal', '-shm', '-journal'):
            name = source.name + suffix
            try:
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise SnapshotError('unsafe database sidecar') from exc
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode):
                    raise SnapshotError('unsafe database sidecar')
                if suffix == '-journal':
                    raise SnapshotError('rollback journal requires explicit recovery')
                digest = hashlib.sha256()
                output_name = 'coordination.evidence' if suffix == '-shm' else 'source.sqlite' + suffix
                output = open(copy_to / output_name, 'xb') if copy_to and suffix in ('', '-wal', '-shm') else None
                try:
                    while True:
                        block = os.read(fd, 1024 * 1024)
                        if not block:
                            break
                        digest.update(block)
                        if output:
                            output.write(block)
                finally:
                    if output:
                        output.close()
                after = os.fstat(fd)
                try:
                    named = os.stat(name, dir_fd=parent, follow_symlinks=False)
                except FileNotFoundError as exc:
                    raise SnapshotError('source changed during snapshot; retry after writers pause') from exc
                def identity(s):
                    return (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
                if identity(info) != identity(after) or identity(info) != identity(named):
                    raise SnapshotError('source changed during snapshot; retry after writers pause')
                result[suffix] = (identity(info), digest.hexdigest())
            finally:
                os.close(fd)
    finally:
        os.close(parent)
    if '' not in result:
        raise SnapshotError('source database is missing')
    if '-shm' in result and '-wal' not in result:
        raise SnapshotError('orphan database coordination file')
    return result


def _validate_wal(path, coordination):
    """Reject incomplete or corrupt frames that SQLite might otherwise ignore."""
    if not path.exists() or path.stat().st_size == 0:
        return
    with path.open('rb') as stream:
        header = stream.read(32)
        if len(header) != 32:
            raise SnapshotError('incomplete source WAL')
        magic, version, page_size, _, salt1, salt2, checksum1, checksum2 = struct.unpack('>8I', header)
        if magic not in (0x377f0682, 0x377f0683) or version != 3007000 or page_size < 512 or page_size > 65536 or page_size & (page_size - 1):
            raise SnapshotError('invalid source WAL header')
        order = '<' if magic == 0x377f0682 else '>'
        def checksum(data, s1=0, s2=0):
            words = struct.unpack(order + str(len(data) // 4) + 'I', data)
            for i in range(0, len(words), 2):
                s1 = (s1 + words[i] + s2) & 0xffffffff
                s2 = (s2 + words[i + 1] + s1) & 0xffffffff
            return s1, s2
        if checksum(header[:24]) != (checksum1, checksum2):
            raise SnapshotError('source WAL header checksum mismatch')
        max_frame = None
        index_checksum = None
        index_pages = None
        if coordination.exists():
            with coordination.open('rb') as index:
                evidence = index.read(96)
            if len(evidence) < 96 or evidence[:48] != evidence[48:96]:
                raise SnapshotError('inconsistent source WAL index')
            index_header = evidence[:48]
            if (struct.unpack_from('=I', index_header, 0)[0] != 3007000 or index_header[12] != 1 or
                index_header[13] != (magic & 1) or
                struct.unpack_from('=H', index_header, 14)[0] != (1 if page_size == 65536 else page_size) or
                index_header[32:40] != header[16:24]):
                raise SnapshotError('source WAL index identity mismatch')
            native_order = '<' if struct.pack('=I', 1)[0] == 1 else '>'
            original_order = order
            order = native_order
            index_sum = checksum(index_header[:40])
            order = original_order
            if index_sum != struct.unpack_from('=2I', index_header, 40):
                raise SnapshotError('source WAL index checksum mismatch')
            max_frame = struct.unpack_from('=I', index_header, 16)[0]
            index_pages = struct.unpack_from('=I', index_header, 20)[0]
            index_checksum = struct.unpack_from('=2I', index_header, 24)
        current = (checksum1, checksum2)
        count = 0
        commit_size = 0
        while frame := stream.read(24):
            if max_frame is not None and count == max_frame:
                while frame:
                    if len(frame) != 24 or len(stream.read(page_size)) != page_size:
                        raise SnapshotError('incomplete source WAL frame')
                    if struct.unpack_from('>2I', frame, 8) == (salt1, salt2):
                        raise SnapshotError('source WAL contains unindexed frames')
                    frame = stream.read(24)
                break
            if len(frame) != 24:
                raise SnapshotError('incomplete source WAL frame')
            page_number, commit_size, frame_salt1, frame_salt2, c1, c2 = struct.unpack('>6I', frame)
            page = stream.read(page_size)
            if len(page) != page_size:
                raise SnapshotError('incomplete source WAL frame')
            if not page_number or (frame_salt1, frame_salt2) != (salt1, salt2):
                raise SnapshotError('source WAL frame identity mismatch')
            current = checksum(frame[:8] + page, *current)
            if current != (c1, c2):
                raise SnapshotError('source WAL frame checksum mismatch')
            count += 1
        if max_frame is not None and (count != max_frame or (count and (not commit_size or commit_size != index_pages or current != index_checksum))):
            raise SnapshotError('source WAL index does not prove committed frames')


def _backup(source, target):
    with tempfile.TemporaryDirectory(prefix='.io-sqlite-', dir=target.parent) as temp:
        private = Path(temp)
        before = _source_files(source)
        copied = _source_files(source, private)
        after = _source_files(source)
        if before != copied or before != after:
            raise SnapshotError('source changed during snapshot; retry after writers pause')
        _validate_wal(private / 'source.sqlite-wal', private / 'coordination.evidence')
        deadline = time.monotonic() + 10
        def progress(status, remaining, total):
            if time.monotonic() > deadline:
                raise SnapshotError('database writers prevented a bounded backup')
        with closing(sqlite3.connect(private / 'source.sqlite')) as src, closing(sqlite3.connect(target)) as dst:
            src.backup(dst, pages=256, progress=progress, sleep=0.05)
            dst.execute('PRAGMA journal_mode=DELETE')
        return before


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
        if version and str(version[0]) == '41':
            _schema41(db)
        return {'schema_sha256': schema_hash, 'tables': tables, 'schema_version': version[0] if version else None,
                'user_version': db.execute('PRAGMA user_version').fetchone()[0],
                'application_id': db.execute('PRAGMA application_id').fetchone()[0]}


def _schema41(db):
    try:
        descriptor = (Path(__file__).parent / 'io_schema41.json').read_bytes()
        if hashlib.sha256(descriptor).hexdigest() != 'b305db3c43167c5734963b1b99a53e3e842413a0ebf25226db7ca729307f2659':
            raise SnapshotError('required schema descriptor is invalid')
        required = json.loads(descriptor)
    except (OSError, ValueError) as exc:
        raise SnapshotError('required schema descriptor is unavailable') from exc
    try:
        semantic_data = (Path(__file__).parent / 'io_schema41_semantics.json').read_bytes()
        if hashlib.sha256(semantic_data).hexdigest() != '9b47bf70bbbe8e6b56d4f6d19bc8bdc0bdd6f2a2e50b148dfde175a0c43db647':
            raise SnapshotError('required schema descriptor is invalid')
        semantics = json.loads(semantic_data)
    except (OSError, ValueError) as exc:
        raise SnapshotError('required schema descriptor is unavailable') from exc
    tables = {row[0].casefold(): row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for name, columns in required.items():
        actual = tables.get(name.casefold())
        if actual is None:
            raise SnapshotError('required schema table missing: ' + name)
        quoted = '"' + actual.replace('"', '""') + '"'
        present = {row[1].casefold() for row in db.execute(f'PRAGMA table_xinfo({quoted})')}
        missing = sorted(c for c in columns if c.casefold() not in present)
        if missing:
            raise SnapshotError('required schema column missing: ' + name + '.' + missing[0])
        current = _table_semantics(db, actual)
        expected = semantics[name]
        if current['primary_key'] != expected['primary_key']:
            raise SnapshotError('required schema invariant missing: ' + name + ' primary key')
        for kind in ('not_null', 'unique', 'foreign_keys', 'checks'):
            if not all(value in current[kind] for value in expected[kind]):
                raise SnapshotError('required schema invariant missing: ' + name + ' ' + kind)


_SQL_TOKEN = re.compile(r'''\s+|--[^\r\n]*|/\*.*?\*/|'(?:''|[^'])*'|"(?:""|[^"])*"|`(?:``|[^`])*`|\[[^\]]*\]|[A-Za-z_][A-Za-z_0-9$]*|\d+(?:\.\d+)?|<=|>=|<>|!=|==|\|\||.''', re.S)


def _sql_tokens(sql):
    return [token for token in _SQL_TOKEN.findall(sql or '')
            if not token.isspace() and not token.startswith(('--', '/*'))]


def _normalized_expression(tokens):
    while len(tokens) >= 2 and tokens[0] == '(' and tokens[-1] == ')':
        depth = 0
        for index, token in enumerate(tokens):
            depth += (token == '(') - (token == ')')
            if depth == 0 and index != len(tokens) - 1:
                return _normalized_expression_tokens(tokens)
        tokens = tokens[1:-1]
    return _normalized_expression_tokens(tokens)


def _normalized_expression_tokens(tokens):
    result = []
    for token in tokens:
        if token.startswith("'"):
            result.append(token)
        elif token.startswith(('"', '`', '[')):
            result.append(token[1:-1].replace('""', '"').replace('``', '`').casefold())
        else:
            result.append(token.casefold())
    return result


def _checks(sql):
    tokens = _sql_tokens(sql)
    result = []
    for index, token in enumerate(tokens[:-1]):
        if token.casefold() != 'check' or tokens[index + 1] != '(':
            continue
        depth = 1
        end = index + 2
        while end < len(tokens) and depth:
            depth += (tokens[end] == '(') - (tokens[end] == ')')
            end += 1
        if depth:
            raise SnapshotError('required schema invariant malformed')
        result.append(_normalized_expression(tokens[index + 2:end - 1]))
    return sorted(result)


def _table_semantics(db, name):
    quoted = '"' + name.replace('"', '""') + '"'
    columns = db.execute(f'PRAGMA table_xinfo({quoted})').fetchall()
    primary = sorted(row[1].casefold() for row in columns if row[5])
    not_null = sorted(row[1].casefold() for row in columns if row[3])
    unique = []
    for index in db.execute(f'PRAGMA index_list({quoted})'):
        if not index[2]:
            continue
        index_name = index[1]
        index_quoted = '"' + index_name.replace('"', '""') + '"'
        index_keys = [row for row in db.execute(f'PRAGMA index_xinfo({index_quoted})') if row[5]]
        if not index_keys or any(row[2] is None for row in index_keys):
            continue
        keys = [(row[2].casefold(), (row[4] or '').casefold()) for row in index_keys]
        predicate = None
        if index[4]:
            row = db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name=?", (index_name,)).fetchone()
            tokens = _sql_tokens(row[0] if row else '')
            depth = 0
            where = None
            for position, token in enumerate(tokens):
                depth += (token == '(') - (token == ')')
                if depth == 0 and token.casefold() == 'where':
                    where = position
                    break
            if where is None:
                raise SnapshotError('required schema invariant malformed')
            predicate = _normalized_expression(tokens[where + 1:])
        unique.append([sorted([list(key) for key in keys]), predicate])
    groups = {}
    for row in db.execute(f'PRAGMA foreign_key_list({quoted})'):
        group = groups.setdefault(row[0], {'table': row[2].casefold(), 'update': row[5].casefold(), 'delete': row[6].casefold(), 'match': row[7].casefold(), 'columns': []})
        group['columns'].append([row[3].casefold(), row[4].casefold() if row[4] is not None else None])
    foreign = []
    for group in groups.values():
        group['columns'].sort(key=lambda pair: (pair[0], pair[1] or ''))
        foreign.append(group)
    sql = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()[0]
    return {'primary_key': primary, 'not_null': not_null, 'unique': unique, 'foreign_keys': foreign, 'checks': _checks(sql)}


def _asset_bindings(path, assets, roots, asset_dirs, image_aliases):
    """Bind recognized operational file references without rewriting source rows."""
    bindings = []
    matched_aliases = set()
    def bind(table, column, identity, value, expected=None, size=None, relative_root=None, allow_reserved=False):
        if not isinstance(value, str) or not value or '\x00' in value or '\\' in value:
            raise SnapshotError('invalid required asset reference')
        if relative_root and not Path(value).is_absolute():
            root, relative = relative_root, value
        else:
            p = Path(value)
            if not p.is_absolute() or any(part in ('.', '..') for part in value.split('/')):
                raise SnapshotError('unresolved asset root')
            matches = [(name, p.relative_to(base).as_posix()) for name, base in roots.items() if p.is_relative_to(base) and p != base]
            if not matches:
                raise SnapshotError('unresolved asset root')
            root, relative = sorted(matches, key=lambda item: (-len(roots[item[0]].parts), item[0]))[0]
        if any(part in ('', '.', '..') for part in relative.split('/')):
            raise SnapshotError('unsafe asset reference')
        evidence = assets.get(root, {}).get(relative)
        if not isinstance(evidence, dict):
            if allow_reserved and relative not in assets.get(root, {}):
                bindings.append({'table': table, 'column': column, 'id': identity, 'root': root, 'path': relative, 'sha256': None, 'state': 'reserved'})
                return
            raise SnapshotError('required asset missing')
        if expected and evidence['sha256'] != expected:
            raise SnapshotError('required asset hash mismatch')
        if size is not None and evidence['size'] != size:
            raise SnapshotError('required asset size mismatch')
        bindings.append({'table': table, 'column': column, 'id': identity, 'root': root, 'path': relative, 'sha256': evidence['sha256']})
    def markup(table, column, identity, text, document=None):
        inventory = inventory_markdown_images(text)
        if inventory.review:
            raise SnapshotError('image inventory requires review: ' + inventory.review[0].kind)
        for occurrence in inventory.occurrences:
            target = occurrence.target
            parsed = urlsplit(target)
            if parsed.scheme.lower() in ('http', 'https', 'data') or target.startswith('//'):
                continue
            if parsed.scheme or parsed.netloc:
                raise SnapshotError('unsupported image reference scheme')
            target = unquote(parsed.path)
            if document:
                root = 'vault'
                relative = posixpath.normpath(posixpath.join(posixpath.dirname(document), target)) if not target.startswith('/') else posixpath.normpath(target.lstrip('/'))
                if relative in ('', '.', '..') or relative.startswith('../') or '\\' in target:
                    raise SnapshotError('image path escapes vault')
                matching = [(i, a) for i, a in enumerate(image_aliases) if isinstance(a, dict) and a.get('owner_document_relative_path') == document and
                            (a.get('target') or a.get('occurrence_index') is not None) and
                            (not a.get('target') or (isinstance(a.get('target'), str) and a['target'].strip() == occurrence.target)) and
                            (a.get('occurrence_index') is None or a.get('occurrence_index') == occurrence.index)]
                matched_aliases.update(i for i, _ in matching)
                if relative not in assets.get('vault', {}):
                    alias_fields = ('document_source_hash', 'target', 'occurrence_index', 'shared_relative_path', 'expected_source_sha256', 'owner_evidence', 'owner_document_relative_path')
                    candidates = [a for _, a in matching]
                    if not candidates or any(tuple(a.get(k) for k in alias_fields) != tuple(candidates[0].get(k) for k in alias_fields) for a in candidates[1:]):
                        raise SnapshotError('local image missing or reviewed alias ambiguous')
                    alias = candidates[0]
                    shared = alias.get('shared_relative_path')
                    expected = alias.get('expected_source_sha256')
                    shared = posixpath.normpath(shared.strip()) if isinstance(shared, str) and shared.strip() and '\\' not in shared and '\x00' not in shared and not shared.startswith('/') else ''
                    expected = expected.strip() if isinstance(expected, str) else ''
                    doc_hash = alias.get('document_source_hash')
                    if ((doc_hash.strip() if isinstance(doc_hash, str) else '') != hashlib.sha256(text.encode()).hexdigest() or
                        not isinstance(alias.get('owner_evidence'), str) or not alias['owner_evidence'].strip() or
                        not document.startswith('raw/') or not document.lower().endswith('.md') or document.startswith('raw/images/') or
                        not shared.startswith('raw/images/') or
                        any(part in ('', '.', '..') for part in shared.split('/')) or
                        not re.fullmatch(r'[0-9a-f]{64}', expected)):
                        raise SnapshotError('reviewed image alias evidence invalid')
                    relative = shared
                    alias_hash = expected
                else:
                    alias_hash = None
            elif re.fullmatch(r'(?:\./)?images/[A-Za-z0-9_-][A-Za-z0-9_.-]{0,179}\.(?:png|jpe?g|gif|webp)', target, re.I):
                root = 'paper_images'
                relative = target.removeprefix('./').removeprefix('images/')
                alias_hash = None
            else:
                raise SnapshotError('image reference has no document root')
            col = column + '.' + target
            previous = next((b for b in bindings if b['table'] == table and b['column'] == col and b['id'] == identity), None)
            if previous and (previous['root'], previous['path']) != (root, relative):
                col += f'#occurrence={occurrence.index}'
                previous = None
            if not previous:
                bind(table, col, identity, relative, alias_hash, relative_root=root)
                if root == 'paper_images':
                    image = _read_file(asset_dirs[root], relative)
                    if (len(image) > 4 * 1024 * 1024 or
                        not (image.startswith((b'\x89PNG\r\n\x1a\n', b'\xff\xd8\xff', b'GIF87a', b'GIF89a')) or
                             (image[:4] == b'RIFF' and image[8:12] == b'WEBP'))):
                        raise SnapshotError('unsupported reader image')
            # Service.raw_asset resolves direct Markdown and HTML src references
            # through its separately configured paper image root.
            reader_name = target.removeprefix('./')
            if document and table in ('body_texts', 'literature_raws', 'raw_snapshots', 'private_raw_sources') and re.fullmatch(r'images/[A-Za-z0-9_-][A-Za-z0-9_.-]{0,179}\.(?:png|jpe?g|gif|webp)', reader_name, re.I):
                pattern = r'''(?:!\[[^\]\n]*\]\(\s*<?|\bsrc\s*=\s*["'])(?:\./)?''' + re.escape(reader_name) + r'''(?=[>\s)"'])'''
                reader_col = column + '.raw_asset:' + reader_name
                if re.search(pattern, text) and not any(b['table'] == table and b['column'] == reader_col and b['id'] == identity for b in bindings):
                    bind(table, reader_col, identity, reader_name.removeprefix('images/'), relative_root='paper_images')
                    reader_image = _read_file(asset_dirs['paper_images'], reader_name.removeprefix('images/'))
                    if (len(reader_image) > 4 * 1024 * 1024 or
                        not (reader_image.startswith((b'\x89PNG\r\n\x1a\n', b'\xff\xd8\xff', b'GIF87a', b'GIF89a')) or
                             (reader_image[:4] == b'RIFF' and reader_image[8:12] == b'WEBP'))):
                        raise SnapshotError('unsupported reader image')
    with closing(_db(path)) as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in ('raw_texts', 'draft_texts'):
            if table in tables and db.execute(f'SELECT 1 FROM "{table}" LIMIT 1').fetchone():
                raise SnapshotError('unsupported retained legacy table ' + table)
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
                if state == 'committed' and cleanup == 'cleaned':
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
                    compressed = table == 'literature_assets' and isinstance(value, str) and value.endswith('.gz')
                    bind(table, column, ident, value, None if compressed else expected, relative_root=relative_root)
                    if compressed:
                        binding = bindings[-1]
                        try:
                            if assets[binding['root']][binding['path']]['size'] > 16 * 1024 * 1024:
                                raise SnapshotError('compressed source exceeds limit')
                            encoded = _read_file(asset_dirs[binding['root']], binding['path'])
                            with gzip.GzipFile(fileobj=io.BytesIO(encoded)) as stream:
                                data = stream.read(16 * 1024 * 1024 + 1)
                            if len(data) > 16 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != expected:
                                raise SnapshotError('compressed source hash mismatch')
                        except (OSError, EOFError, zlib.error) as exc:
                            raise SnapshotError('invalid compressed source') from exc
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
                for ident, preimage, quarantine, candidate, state in db.execute('SELECT id, preimage_json, quarantine_path, candidate_hash, state FROM media_raw_activation_intents'):
                    if quarantine:
                        bind('media_raw_activation_intents', 'quarantine_path', ident, quarantine, candidate, allow_reserved=state == 'prepared')
                        if bindings[-1].get('state') != 'reserved' and not candidate:
                            raise SnapshotError('quarantine has no immutable byte evidence')
                    if preimage:
                        try:
                            data = json.loads(preimage)
                            bind('media_raw_activation_intents', 'preimage_json.staging_path', ident, data['staging_path'], data['document_hash'])
                        except (ValueError, TypeError, KeyError) as exc:
                            raise SnapshotError('invalid recovery preimage') from exc
        for table, key in (('body_texts', 'snapshot_id'), ('draft_bodies', 'draft_id')):
            if table in tables:
                for ident, text in db.execute(f'SELECT "{key}", text FROM "{table}"'):
                    versions = 'body_versions' if table == 'body_texts' else 'draft_versions'
                    mappings = 'literature_raws' if table == 'body_texts' else 'literature_drafts'
                    document = None
                    if versions in tables and mappings in tables:
                        row = db.execute(f'SELECT m.path FROM "{versions}" v JOIN "{mappings}" m ON m."{key}"=v."{key}" WHERE v."{key}"=? AND v.authority=\'imported\'', (ident,)).fetchone()
                        document = row[0] if row else None
                    markup(table, 'text', ident, text, document)
        for binding in list(bindings):
            if binding['table'] in ('literature_raws', 'literature_drafts', 'raw_snapshots', 'private_raw_sources'):
                try:
                    body = _read_file(asset_dirs[binding['root']], binding['path']).decode('utf-8')
                except UnicodeDecodeError as exc:
                    raise SnapshotError('referenced document is not UTF-8') from exc
                markup(binding['table'], binding['column'], binding['id'], body,
                       binding['path'] if binding['root'] == 'vault' else None)
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
                                        reserved = False
                                        if table == 'media_raw_activation_intents' and key_path == 'old_authority_json.path':
                                            state = db.execute('SELECT state, preimage_json FROM media_raw_activation_intents WHERE rowid=?', (rowid,)).fetchone()
                                            reserved = state == ('prepared', None)
                                        digest = obj.get('file_hash') if key.lower() in ('archive_path', 'archivepath') else None
                                        bind(table, key_path, rowid, nested, digest, relative_root='vault' if name in ('old_mapping_json', 'old_authority_json') else None, allow_reserved=reserved)
                                    else:
                                        visit(nested, key_path)
                            elif isinstance(obj, list):
                                for index, nested in enumerate(obj):
                                    visit(nested, trail + f'[{index}]')
                        visit(value, name)
    if len(matched_aliases) != len(image_aliases):
        raise SnapshotError('reviewed image alias does not match a local document reference')
    ordered = sorted(bindings, key=lambda x: (x['table'], x['column'], str(x['id'])))
    identities = [(b['table'], b['column'], b['id']) for b in ordered]
    if len(set(identities)) != len(identities):
        raise SnapshotError('duplicate asset identity')
    return ordered


def _coverage(path):
    fields = []
    explicit = {
        ('body_texts', 'text'): 'source_image_inventory',
        ('draft_bodies', 'text'): 'source_image_inventory',
        ('literature_assets', 'metadata_json'): 'retained_image_archive_metadata',
        ('media_objects', 'public_url'): 'remote_reference_not_verified',
        ('media_objects', 'stored_sha256'): 'remote_expected_hash',
        ('media_upload_intents', 'payload'): 'database_blob',
        ('media_pending', 'source_ref'): 'source_reference_with_staged_payload',
        ('media_usages', 'source_ref'): 'remote_usage_reference',
    }
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
                if (table, name) in explicit:
                    fields.append([table, name, explicit[(table, name)]])
    return fields


def _references(path, assets, bindings):
    """Validate known file authorities; reject unsupported live references."""
    with closing(_db(path)) as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'media_objects' in tables:
            columns = {r[1] for r in db.execute('PRAGMA table_info(media_objects)')}
            if not {'key', 'stored_sha256', 'bytes'} <= columns:
                raise SnapshotError('unsupported managed object schema')
            deleted = 'deleted_at' if 'deleted_at' in columns else 'NULL'
            preserved = {(entry['sha256'], entry['size']) for tree in assets.values()
                         for entry in tree.values() if isinstance(entry, dict)}
            for key, digest, size, removed in db.execute(f'SELECT key, stored_sha256, bytes, {deleted} FROM media_objects'):
                if removed or (digest, size) in preserved:
                    continue
                payloads = (db.execute('SELECT payload FROM media_upload_intents WHERE object_key=?', (key,))
                            if 'media_upload_intents' in tables else ())
                if not any(isinstance(payload, bytes) and len(payload) == size
                           and hashlib.sha256(payload).hexdigest() == digest for (payload,) in payloads):
                    raise SnapshotError('managed object has no preserved bytes with matching hash and size')
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
                    imported = 'body_versions' in tables and db.execute("SELECT 1 FROM body_versions WHERE snapshot_id=? AND authority='imported'", (ident,)).fetchone()
                    if imported and not mapped:
                        raise SnapshotError('imported raw has no authoritative file mapping')
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
                version = db.execute('SELECT item_id, authority FROM draft_versions WHERE draft_id=?', (ident,)).fetchone() if 'draft_versions' in tables else None
                if version and version[1] == 'imported' and not mapping:
                    raise SnapshotError('imported draft has no authoritative file mapping')
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


def snapshot(database, roots, destination, *, image_aliases=None):
    database = Path(database)
    if database.is_symlink() or not database.is_file():
        raise SnapshotError('source database is missing or unsafe')
    if not roots or any(not re.fullmatch(r'[a-z][a-z0-9_]*', name) for name in roots):
        raise SnapshotError('explicit named asset roots required')
    roots = {name: Path(path) for name, path in roots.items()}
    if image_aliases is None:
        image_aliases = []
    if not isinstance(image_aliases, list) or any(not isinstance(a, dict) for a in image_aliases):
        raise SnapshotError('invalid reviewed image aliases')
    if any(database.resolve().is_relative_to(p.resolve()) or p.resolve().is_relative_to(database.resolve()) for p in roots.values()):
        raise SnapshotError('database overlaps asset roots')
    resolved = {name: p.resolve() for name, p in roots.items()}
    storage = {}
    for name, path in resolved.items():
        parent = min((n for n, p in resolved.items() if path.is_relative_to(p)), key=lambda n: (len(resolved[n].parts), n))
        prefix = path.relative_to(resolved[parent]).as_posix()
        storage[name] = {'root': parent, 'prefix': '' if prefix == '.' else prefix}
    physical = {name: roots[name] for name in roots if storage[name] == {'root': name, 'prefix': ''}}
    destination = _check_destination(destination, [database, *roots.values()])
    with tempfile.TemporaryDirectory(prefix='.io-snapshot-', dir=destination.parent) as temp:
        stage = Path(temp)
        first = {name: _inventory(path) for name, path in roots.items()}
        source_before = _backup(database, stage / 'database.sqlite')
        evidence = _database(stage / 'database.sqlite')
        if evidence['schema_version'] != '41':
            version = evidence['schema_version']
            safe_version = version if isinstance(version, str) and re.fullmatch(r'[0-9]{1,4}', version) else 'unknown'
            raise SnapshotError('unsupported IO schema version ' + safe_version)
        root_bindings = {name: str(path.absolute()) for name, path in roots.items()}
        bindings = _asset_bindings(stage / 'database.sqlite', first, {name: Path(path) for name, path in root_bindings.items()}, roots, image_aliases)
        references = _references(stage / 'database.sqlite', first, bindings)
        for name, path in physical.items():
            _inventory(path, stage / 'assets' / name)
        copied_dirs = _asset_dirs(stage, storage)
        copied = {name: _inventory(copied_dirs[name]) for name in roots}
        second = {name: _inventory(path) for name, path in roots.items()}
        source_after = _backup(database, stage / 'check.sqlite')
        if first != copied or first != second or source_before != source_after or evidence != _database(stage / 'check.sqlite'):
            raise SnapshotError('source changed during snapshot; retry after writers pause')
        (stage / 'check.sqlite').unlink()
        manifest = {'format': 4, 'database_sha256': _hash(stage / 'database.sqlite'), 'database': evidence, 'assets': first, 'remote_reference_counts': references, 'source_roots': root_bindings, 'asset_bindings': bindings, 'reference_coverage': _coverage(stage / 'database.sqlite'), 'asset_storage': storage, 'image_aliases': image_aliases}
        (stage / 'manifest.json').write_text(json.dumps(manifest, sort_keys=True), encoding='utf-8')
        verify(stage)
        _publish(stage, destination)


def _asset_dirs(root, storage):
    result = {}
    for name, binding in storage.items():
        if not isinstance(binding, dict) or set(binding) != {'root', 'prefix'}:
            raise SnapshotError('invalid asset storage')
        parent, prefix = binding['root'], binding['prefix']
        if parent not in storage or storage[parent] != {'root': parent, 'prefix': ''} or not isinstance(prefix, str):
            raise SnapshotError('invalid asset storage')
        if prefix and any(part in ('', '.', '..') for part in prefix.split('/')):
            raise SnapshotError('unsafe asset storage path')
        result[name] = root / 'assets' / parent / prefix
    return result


def verify(directory):
    root = Path(directory)
    try:
        inventory = _inventory(root)
        if set(p.split('/')[0] for p in inventory) != {'database.sqlite', 'manifest.json', 'assets'}:
            raise SnapshotError('unexpected snapshot contents')
        manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
        if set(manifest) != {'format', 'database_sha256', 'database', 'assets', 'remote_reference_counts', 'source_roots', 'asset_bindings', 'reference_coverage', 'asset_storage', 'image_aliases'} or manifest['format'] != 4:
            raise SnapshotError('invalid manifest')
        if not isinstance(manifest['assets'], dict) or not manifest['assets']:
            raise SnapshotError('invalid asset roots')
        names = manifest['assets'].keys()
        if any(not isinstance(n, str) or not re.fullmatch(r'[a-z][a-z0-9_]*', n) for n in names):
            raise SnapshotError('invalid asset root name')
        storage = manifest['asset_storage']
        if not isinstance(storage, dict) or set(storage) != set(names):
            raise SnapshotError('asset storage differs')
        dirs = _asset_dirs(root, storage)
        if {p.name for p in (root / 'assets').iterdir()} != {v['root'] for v in storage.values()}:
            raise SnapshotError('asset roots differ')
        source_roots = manifest['source_roots']
        if not isinstance(source_roots, dict) or set(source_roots) != set(names) or any(not isinstance(p, str) or not Path(p).is_absolute() or '..' in Path(p).parts for p in source_roots.values()):
            raise SnapshotError('invalid source root bindings')
        assets = {n: _inventory(dirs[n]) for n in names}
        if not isinstance(manifest['database'], dict) or manifest['database'].get('schema_version') != '41':
            raise SnapshotError('unsupported IO schema version')
        if assets != manifest['assets'] or _hash(root / 'database.sqlite') != manifest['database_sha256'] or _database(root / 'database.sqlite') != manifest['database']:
            raise SnapshotError('snapshot integrity mismatch')
        if not isinstance(manifest['image_aliases'], list) or any(not isinstance(a, dict) for a in manifest['image_aliases']):
            raise SnapshotError('invalid reviewed image aliases')
        bindings = _asset_bindings(root / 'database.sqlite', assets, {n: Path(p) for n, p in source_roots.items()}, dirs, manifest['image_aliases'])
        if bindings != manifest['asset_bindings'] or _coverage(root / 'database.sqlite') != manifest['reference_coverage'] or _references(root / 'database.sqlite', assets, bindings) != manifest['remote_reference_counts']:
            raise SnapshotError('reference evidence mismatch')
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error) as exc:
        raise SnapshotError('invalid or unreadable snapshot') from exc
    return {'integrity_verified': True, 'coverage': 'incomplete', 'tables': len(manifest['database']['tables']), 'asset_roots': len(assets), 'remote_reference_counts': manifest['remote_reference_counts']}


def _recovery_read(directory, table, column, identity):
    root = Path(directory)
    verify(root)
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    matches = [b for b in manifest['asset_bindings'] if b['table'] == table and b['column'] == column and b['id'] == identity]
    if len(matches) != 1:
        raise SnapshotError('asset reference not uniquely bound')
    binding = matches[0]
    if binding.get('state') == 'reserved':
        raise SnapshotError('asset reference is reserved and has no bytes')
    asset_root = _asset_dirs(root, manifest['asset_storage'])[binding['root']]
    data, info = _read_file_identity(asset_root, binding['path'])
    if hashlib.sha256(data).hexdigest() != binding['sha256']:
        raise SnapshotError('asset changed during read')
    current = {'path': str((asset_root / binding['path']).absolute()), 'sha256': binding['sha256'],
               'size': len(data), 'device': info.st_dev, 'inode': info.st_ino}
    return data, current


def read_asset(directory, table, column, identity):
    """Read a recognized reference from the relocated tree after full validation."""
    return _recovery_read(directory, table, column, identity)[0]


def recovery_binding(directory, table, column, identity):
    """Return fresh restored-file identity for a recovery adapter, not audit data."""
    return _recovery_read(directory, table, column, identity)[1]


def read_recovery_asset(directory, table, column, identity, expected):
    """Revalidate identity and hash immediately before a consumer uses the bytes."""
    data, current = _recovery_read(directory, table, column, identity)
    if current != expected:
        raise SnapshotError('recovery asset identity changed')
    return data


def recovery_adapter(directory, table, column, identity, record):
    """Create ephemeral IO staging fields without changing the historical record."""
    current = recovery_binding(directory, table, column, identity)
    if not isinstance(record, dict) or record.get('document_hash') != current['sha256'] or record.get('document_bytes') != current['size']:
        raise SnapshotError('recovery record does not match restored bytes')
    return {**record, 'staging_path': current['path'], 'staging_device': current['device'], 'staging_inode': current['inode']}


def remote_references(directory):
    """Return remote object identities and expected hashes without fetching them."""
    root = Path(directory)
    verify(root)
    with closing(_db(root / 'database.sqlite')) as db:
        exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='media_objects'").fetchone()
        if not exists:
            return []
        cols = {r[1] for r in db.execute('PRAGMA table_info(media_objects)')}
        if not {'key', 'namespace', 'stored_sha256'} <= cols:
            raise SnapshotError('unsupported remote object schema')
        deleted = 'deleted_at' if 'deleted_at' in cols else 'NULL'
        return [{'key': key, 'namespace': namespace, 'expected_sha256': digest,
                 'status': 'deleted_record' if removed else 'requires_live_readback'}
                for key, namespace, digest, removed in db.execute(f'SELECT key, namespace, stored_sha256, {deleted} FROM media_objects ORDER BY key')]


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
    make.add_argument('--image-aliases', metavar='JSON_FILE')
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
            aliases = json.loads(Path(args.image_aliases).read_text(encoding='utf-8')) if args.image_aliases else None
            snapshot(args.database, roots, args.destination, image_aliases=aliases)
        elif args.command == 'verify':
            print(json.dumps(verify(args.snapshot), sort_keys=True))
            return 0
        else:
            restore(args.snapshot, args.destination)
        print('OK (limited coverage; see T01 acceptance notes)')
    except (SnapshotError, OSError, sqlite3.Error, ValueError) as exc:
        print('Snapshot refused: ' + (str(exc) if isinstance(exc, SnapshotError) else 'filesystem or database error'))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
