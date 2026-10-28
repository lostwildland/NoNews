"""Bounded JSON encoding of SQLite TEXT values for managed job snapshots."""
import codecs
import json
import re
import tempfile

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
    code = 'job_record_too_large'


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

    def text_column_steps(self, db, table, column, rowid):
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
                yield None
            tail = decoder.decode(b'', final=True)
            if tail:
                self.write(json.dumps(tail, ensure_ascii=False)[1:-1].encode('utf-8'))
            self.write(b'"')

    def text_column(self, db, table, column, rowid):
        for _ in self.text_column_steps(db, table, column, rowid):
            pass


class _AggregateJSON:
    """Validate an aggregate document and retain only failed stage statuses."""
    _special = re.compile(r'["\\\\\x00-\x1f]')
    _stages = frozenset(('scoring', 'acquisition', 'curator', 'editor'))

    def __init__(self, chunks, directory=None):
        self.directory = directory
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

    def whitespace_steps(self):
        steps = 0
        while self.peek() and self.peek() in ' \t\r\n':
            self.pos += 1
            steps += 1
            if steps == 4096:
                steps = 0
                yield None

    def string_steps(self, capture):
        if self.take() != '"':
            raise ValueError('invalid JSON string')
        raw = ['"'] if capture else None
        length = 1
        steps = 0
        while self.peek():
            steps += 1
            if steps == 4096:
                steps = 0
                yield None
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

    def scalar_steps(self, role):
        yield from self.whitespace_steps()
        char = self.peek()
        if char == '"':
            value = yield from self.string_steps(role == 3)
            return value if role == 3 else None
        for literal in ('true', 'false', 'null', 'NaN', 'Infinity'):
            if char == literal[0]:
                if ''.join(self.take() for _ in literal) != literal:
                    raise ValueError('invalid JSON literal')
                return None
        yield from self.number_steps()
        return None

    def number_steps(self):
        steps = 0
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
                steps += 1
                if steps == 4096:
                    steps = 0
                    yield None
        else:
            raise ValueError('invalid JSON number')
        if self.peek() == '.':
            self.take()
            if not self.peek() or self.peek() not in '0123456789':
                raise ValueError('invalid JSON fraction')
            while self.peek() and self.peek() in '0123456789':
                self.take()
                steps += 1
                if steps == 4096:
                    steps = 0
                    yield None
        if self.peek() and self.peek() in 'eE':
            self.take()
            if self.peek() and self.peek() in '+-':
                self.take()
            if not self.peek() or self.peek() not in '0123456789':
                raise ValueError('invalid JSON exponent')
            while self.peek() and self.peek() in '0123456789':
                self.take()
                steps += 1
                if steps == 4096:
                    steps = 0
                    yield None

    def failed_stages_steps(self):
        # Container state uses one byte per nesting level and spills beyond 64 KiB.
        with tempfile.SpooledTemporaryFile(max_size=65536, mode='w+b', dir=self.directory) as stack:
            depth = 0
            block = bytearray()
            results = {}
            keys = {}
            root = None
            complete = False

            def get_state():
                value = block[-1]
                return value & 7, value >> 3

            def set_state(state, role):
                block[-1] = state | (role << 3)

            def push(state, role):
                nonlocal depth
                if len(block) == 65536:
                    stack.seek(depth - len(block))
                    if stack.write(block) != len(block):
                        raise OSError('incomplete aggregate stack write')
                    block.clear()
                block.append(state | (role << 3))
                depth += 1
                if state == 0 and role in (0, 1, 2):
                    results[depth] = {}

            def deliver(value):
                nonlocal root, complete
                if depth == 0:
                    root = value
                    complete = True
                    return
                state, role = get_state()
                if state == 3:
                    key = keys.pop(depth, None)
                    if depth in results and ((role == 0 and key == 'stages') or
                                             (role == 1 and key in self._stages) or
                                             (role == 2 and key == 'status')):
                        results[depth][key] = value
                    set_state(4, role)
                elif state in (5, 6):
                    set_state(7, role)
                else:
                    raise ValueError('invalid JSON value position')

            def close_container():
                nonlocal depth
                value = results.pop(depth, None)
                keys.pop(depth, None)
                block.pop()
                depth -= 1
                if not block and depth:
                    size = min(depth, 65536)
                    stack.seek(depth - size)
                    block.extend(stack.read(size))
                    if len(block) != size:
                        raise OSError('incomplete aggregate stack read')
                deliver(value)

            def begin_value(role):
                yield from self.whitespace_steps()
                char = self.peek()
                if char == '{':
                    self.take()
                    push(0, role)
                elif char == '[':
                    self.take()
                    push(5, 4)
                else:
                    deliver((yield from self.scalar_steps(role)))

            try:
                yield from begin_value(0)
                steps = 0
                while not complete:
                    steps += 1
                    if steps == 4096:
                        steps = 0
                        yield None
                    state, role = get_state()
                    yield from self.whitespace_steps()
                    char = self.peek()
                    if state in (0, 1):
                        if state == 0 and char == '}':
                            self.take()
                            close_container()
                        else:
                            if role in (0, 1, 2):
                                keys[depth] = yield from self.string_steps(True)
                            else:
                                yield from self.string_steps(False)
                            set_state(2, role)
                    elif state == 2:
                        if self.take() != ':':
                            raise ValueError('invalid JSON object')
                        set_state(3, role)
                    elif state == 3:
                        key = keys.get(depth)
                        child_role = (1 if role == 0 and key == 'stages' else
                                      2 if role == 1 and key in self._stages else
                                      3 if role == 2 and key == 'status' else 4)
                        yield from begin_value(child_role)
                    elif state == 4:
                        separator = self.take()
                        if separator == '}':
                            close_container()
                        elif separator == ',':
                            set_state(1, role)
                        else:
                            raise ValueError('invalid JSON object separator')
                    elif state in (5, 6):
                        if state == 5 and char == ']':
                            self.take()
                            close_container()
                        else:
                            yield from begin_value(4)
                    else:
                        separator = self.take()
                        if separator == ']':
                            close_container()
                        elif separator == ',':
                            set_state(6, role)
                        else:
                            raise ValueError('invalid JSON array separator')
                yield from self.whitespace_steps()
                if self.peek():
                    raise ValueError('trailing JSON')
            except ValueError:
                return ()
        stages = root.get('stages') if isinstance(root, dict) else None
        if not isinstance(stages, dict):
            return ()
        return tuple(stage for stage, detail in stages.items()
                     if isinstance(detail, dict) and detail.get('status') == 'failed')


def aggregate_failed_stages_steps(chunks, directory=None):
    return (yield from _AggregateJSON(chunks, directory).failed_stages_steps())


def aggregate_failed_stages(chunks, directory=None):
    steps = aggregate_failed_stages_steps(chunks, directory)
    while True:
        try:
            next(steps)
        except StopIteration as result:
            return result.value
