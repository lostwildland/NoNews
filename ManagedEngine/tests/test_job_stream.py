from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.job_stream import CHUNK_BYTES, SnapshotTooLarge, SnapshotWriter


class JobStreamTest(unittest.TestCase):
    def test_blob_text_escaping_and_capacity(self):
        with tempfile.TemporaryDirectory() as temp:
            with closing(sqlite3.connect(Path(temp) / 'test.sqlite')) as db:
                db.execute('CREATE TABLE sample (value TEXT)')
                original = 'x' * (CHUNK_BYTES - 1) + '😀"\\\n\u0000中' * 10000
                db.execute('INSERT INTO sample VALUES (?)', (original,))
                with tempfile.TemporaryFile() as output:
                    writer = SnapshotWriter(output)
                    writer.text_column(db, 'sample', 'value', 1)
                    output.seek(0)
                    self.assertEqual(json.loads(output.read()), original)
                with tempfile.TemporaryFile() as output:
                    writer = SnapshotWriter(output, limit=len(original.encode('utf-8')) + 1)
                    with self.assertRaises(SnapshotTooLarge):
                        writer.text_column(db, 'sample', 'value', 1)
                    self.assertEqual(output.tell(), 0)
                with tempfile.TemporaryFile() as output:
                    writer = SnapshotWriter(output, limit=len(original.encode('utf-8')) + 2)
                    with self.assertRaises(SnapshotTooLarge):
                        writer.text_column(db, 'sample', 'value', 1)

    def test_utf16_database_text_is_encoded_as_utf8_json(self):
        with tempfile.TemporaryDirectory() as temp, closing(sqlite3.connect(Path(temp) / 'utf16.sqlite')) as db:
            db.execute("PRAGMA encoding='UTF-16le'")
            db.execute('CREATE TABLE sample (value TEXT)')
            original = 'x'*8191 + '😀"\\\n中'*5000
            db.execute('INSERT INTO sample VALUES (?)', (original,))
            with tempfile.TemporaryFile() as output:
                writer = SnapshotWriter(output)
                writer.text_column(db, 'sample', 'value', 1)
                output.seek(0)
                self.assertEqual(json.loads(output.read()), original)

    def test_streamed_cause_matches_original_reference(self):
        import re
        from backend import causes
        def reference(value):
            value = str(value or '').lower()
            if any(x in value for x in ('papererror:', 'publisher:', 'source fetch')) and 'http 403' in value:
                return causes.SOURCE_BROWSER
            if 'paper abstract lookup' in value and 'http 429' in value:
                return causes.REMOTE_ERROR
            if re.search(r'api[_ ]key\w*\s+(?:is\s+)?(?:missing|invalid|not configured)', value):
                return causes.PROVIDER_AUTH
            for cause, terms in causes._RULES:
                if any(term in value for term in terms):
                    return cause
            return causes.UNKNOWN
        samples = [None, '', 'quota HTTP 401', 'PaperError: ' + 'x'*70000 + ' HTTP 403',
                   'paper abstract lookup ' + 'x'*70000 + ' HTTP 429',
                   'api_key' + 'x'*70000 + ' \t is \n not configured',
                   'api_key' + 'x'*70000 + ' foo', 'api_key is invalid',
                   'api_key isis missing', 'API KEY invalid', 'gateway timeout',
                   'api_key  is invalid api_key is missing']
        samples += [term for _, terms in causes._RULES for term in terms]
        for sample in samples:
            text = str(sample or '')
            expected = reference(sample)
            for width in (1, 7, 16384):
                with self.subTest(sample=text[:30], width=width):
                    self.assertEqual(causes.classify_chunks(text[i:i+width] for i in range(0, len(text), width)), expected)
                    self.assertEqual(causes.classify(sample), expected)

    def test_large_error_combines_distant_signals_without_large_allocation(self):
        import tracemalloc
        from backend import causes
        value = 'papererror:' + 'x'*(16*1024*1024) + ' HTTP 403'
        tracemalloc.start()
        try:
            result = causes.classify_chunks(value[i:i+16384] for i in range(0,len(value),16384))
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        self.assertEqual(result, causes.SOURCE_BROWSER)
        self.assertLess(peak, 4*1024*1024)

    def test_aggregate_projection_matches_json_reference_across_boundaries(self):
        from backend.job_stream import aggregate_failed_stages
        valid = [
            '{}', 'null', '[]', '{"stages":null}', '{"stages":[]}',
            '{"stages":{"curator":{"status":"failed"},"editor":{"status":"failed"}}}',
            '{"stages":{"curator":{"status":"failed","status":"ready"}}}',
            '{"stages":{"curator":{"status":"ready"},"curator":{"status":"failed"}}}',
            '{"stages":{"curator":{"status":"failed"}},"stages":null}',
            '{"stages":{"\\u0063urator":{"status":"f\\u0061iled"}},"other":[null,true,-Infinity,NaN,1.2e-3]}',
            '{"stages":{"editor":{"status":false},"acquisition":null,"unknown":{"status":"failed"}}}',
            '{"stages":{"scoring":{"status":"failed"}},"ignored":{"nested":"' + 'x'*70000 + '😀\\\\\\""}}',
        ]
        invalid = ['', '{', '{"stages":', '{"stages":{"curator":{"status":"failed"}}} trailing',
                   '{"stages":{"curator":{"status":"failed"}},"bad":"\\q"}',
                   '{"stages":{"curator":{"status":"failed"}},"bad":[1,]}',
                   '{"stages":{"curator":{"status":"failed"}},"bad":01}']
        for text in valid + invalid:
            try:
                value = json.loads(text)
                stages = value.get('stages') if isinstance(value, dict) else None
                expected = tuple(k for k,v in stages.items() if k in {'scoring','acquisition','curator','editor'} and isinstance(v,dict) and v.get('status') == 'failed') if isinstance(stages,dict) else ()
            except json.JSONDecodeError:
                expected = ()
            for size in (1, 7, 16384):
                with self.subTest(text=text[:60], size=size):
                    self.assertEqual(aggregate_failed_stages(text[i:i+size] for i in range(0,len(text),size)), expected)

    def test_deep_nesting_uses_bounded_projection_memory(self):
        import tracemalloc
        from backend.job_stream import aggregate_failed_stages
        for opening, closing in (('[', ']'), ('{"x":', '}')):
            text = '{"ignored":' + opening*70000 + '0' + closing*70000 + ',"stages":{"curator":{"status":"failed"}}}'
            tracemalloc.start()
            try:
                stages = aggregate_failed_stages(text[i:i+16384] for i in range(0,len(text),16384))
                peak = tracemalloc.get_traced_memory()[1]
            finally:
                tracemalloc.stop()
            self.assertEqual(stages, ('curator',))
            self.assertLess(peak, 4*1024*1024, (opening, peak))
