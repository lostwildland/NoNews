"""Bounded JSON encoding of SQLite TEXT values for managed job snapshots."""
import codecs
import json
import re

CHUNK_BYTES = 16384


def _encoding(db):
    return {'UTF-8': 'utf-8', 'UTF-16le': 'utf-16-le', 'UTF-16be': 'utf-16-be'}[db.execute('PRAGMA encoding').fetchone()[0]]
SNAPSHOT_CAPACITY = 512 * 1024 * 1024


def text_chunks(db, table, column, rowid):
    with db.blobopen(table, column, rowid, readonly=True) as blob:
        decoder = codecs.getincrementaldecoder(_encoding(db))('strict')
        while chunk := blob.read(CHUNK_BYTES):
            text = decoder.decode(chunk)
            if text:
                yield text
        tail = decoder.decode(b'', final=True)
        if tail:
            yield tail


class SnapshotTooLarge(ValueError):
    pass


class SnapshotWriter:
    def __init__(self, output, limit=SNAPSHOT_CAPACITY):
        self.output = output
        self.limit = limit
        self.size = 0

    def write(self, value):
        size = self.size + len(value)
        if size > self.limit:
            raise SnapshotTooLarge('record exceeds snapshot capacity')
        if self.output.write(value) != len(value):
            raise OSError('incomplete snapshot write')
        self.size = size

    def value(self, value):
        self.write(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))

    def text_column(self, db, table, column, rowid):
        """Write a TEXT cell, with bounded UTF-8 decoding and JSON escaping."""
        with db.blobopen(table, column, rowid, readonly=True) as blob:
            # Even without JSON escaping, these bytes and the quotes must fit.
            minimum = len(blob) if _encoding(db) == 'utf-8' else (len(blob) + 1) // 2
            if self.size + minimum + 2 > self.limit:
                raise SnapshotTooLarge('record exceeds snapshot capacity')
            decoder = codecs.getincrementaldecoder(_encoding(db))('strict')
            self.write(b'"')
            while chunk := blob.read(CHUNK_BYTES):
                text = decoder.decode(chunk)
                if text:
                    self.write(json.dumps(text, ensure_ascii=False)[1:-1].encode('utf-8'))
            tail = decoder.decode(b'', final=True)
            if tail:
                self.write(json.dumps(tail, ensure_ascii=False)[1:-1].encode('utf-8'))
            self.write(b'"')


class _AggregateJSON:
    """Validate an aggregate document and retain only failed stage statuses."""
    _special = re.compile(r'["\\\\\x00-\x1f]')
    _stages = frozenset(('scoring', 'acquisition', 'curator', 'editor'))

    def __init__(self, chunks):
        self.chunks = iter(chunks)
        self.buffer = ''
        self.pos = 0

    def peek(self):
        while self.pos == len(self.buffer):
            try:
                self.buffer = next(self.chunks)
                self.pos = 0
            except StopIteration:
                return ''
        return self.buffer[self.pos]

    def take(self):
        char = self.peek()
        if char:
            self.pos += 1
        return char

    def whitespace(self):
        while self.peek() and self.peek() in ' \t\r\n':
            self.pos += 1

    def string(self, capture):
        if self.take() != '"':
            raise ValueError('invalid JSON string')
        raw = ['"'] if capture else None
        length = 1
        while self.peek():
            match = self._special.search(self.buffer, self.pos)
            end = match.start() if match else len(self.buffer)
            segment = self.buffer[self.pos:end]
            self.pos = end
            length += len(segment)
            if raw is not None:
                if length <= 512:
                    raw.append(segment)
                else:
                    raw = None
            if not match:
                continue
            char = self.take()
            if char == '"':
                if raw is None:
                    return None
                raw.append('"')
                return json.loads(''.join(raw))
            if char != '\\':
                raise ValueError('invalid JSON control character')
            escape = self.take()
            if escape not in '"\\/bfnrtu' or not escape:
                raise ValueError('invalid JSON escape')
            escaped = '\\' + escape
            if escape == 'u':
                digits = ''.join(self.take() for _ in range(4))
                if len(digits) != 4 or any(ch not in '0123456789abcdefABCDEF' for ch in digits):
                    raise ValueError('invalid JSON unicode escape')
                escaped += digits
            length += len(escaped)
            if raw is not None:
                if length <= 512:
                    raw.append(escaped)
                else:
                    raw = None
        raise ValueError('unterminated JSON string')

    def value(self, role='skip', depth=0):
        self.whitespace()
        char = self.peek()
        if char == '{':
            self.take()
            result = {} if role in ('root', 'stages', 'entry') else None
            self.whitespace()
            if self.peek() == '}':
                self.take()
                return result
            while True:
                self.whitespace()
                key = self.string(result is not None)
                self.whitespace()
                if self.take() != ':':
                    raise ValueError('invalid JSON object')
                child_role = ('stages' if role == 'root' and key == 'stages' else
                              'entry' if role == 'stages' and key in self._stages else
                              'status' if role == 'entry' and key == 'status' else 'skip')
                value = self.value(child_role, depth + 1)
                if result is not None and child_role != 'skip':
                    result[key] = value
                self.whitespace()
                separator = self.take()
                if separator == '}':
                    return result
                if separator != ',':
                    raise ValueError('invalid JSON object separator')
        if char == '[':
            self.take()
            self.whitespace()
            if self.peek() == ']':
                self.take()
                return None
            while True:
                self.value('skip', depth + 1)
                self.whitespace()
                separator = self.take()
                if separator == ']':
                    return None
                if separator != ',':
                    raise ValueError('invalid JSON array separator')
        if char == '"':
            value = self.string(role == 'status')
            return value if role == 'status' else None
        for literal in ('true', 'false', 'null', 'NaN', 'Infinity'):
            if char == literal[0]:
                if ''.join(self.take() for _ in literal) != literal:
                    raise ValueError('invalid JSON literal')
                return None
        self.number()
        return None

    def number(self):
        if self.peek() == '-':
            self.take()
            if self.peek() == 'I':
                if ''.join(self.take() for _ in 'Infinity') != 'Infinity':
                    raise ValueError('invalid JSON literal')
                return
        if self.peek() == '0':
            self.take()
        elif self.peek() and self.peek() in '123456789':
            while self.peek() and self.peek() in '0123456789':
                self.take()
        else:
            raise ValueError('invalid JSON number')
        if self.peek() == '.':
            self.take()
            if not self.peek() or self.peek() not in '0123456789':
                raise ValueError('invalid JSON fraction')
            while self.peek() and self.peek() in '0123456789':
                self.take()
        if self.peek() and self.peek() in 'eE':
            self.take()
            if self.peek() and self.peek() in '+-':
                self.take()
            if not self.peek() or self.peek() not in '0123456789':
                raise ValueError('invalid JSON exponent')
            while self.peek() and self.peek() in '0123456789':
                self.take()

    def failed_stages(self):
        try:
            root = self.value('root')
            self.whitespace()
            if self.peek():
                raise ValueError('trailing JSON')
        except ValueError:
            return ()
        stages = root.get('stages') if isinstance(root, dict) else None
        if not isinstance(stages, dict):
            return ()
        return tuple(stage for stage, detail in stages.items()
                     if isinstance(detail, dict) and detail.get('status') == 'failed')


def aggregate_failed_stages(chunks):
    return _AggregateJSON(chunks).failed_stages()
