import json
from pathlib import Path
import subprocess
import tempfile
import unittest


class ChannelTest(unittest.TestCase):
    def test_rejects_bad_requests_and_strips_ambient_flags(self):
        project = Path(__file__).resolve().parents[1]
        python = project / '.prepared/python/bin/python3'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            backend = root / 'backend'
            backend.mkdir()
            (backend / '__init__.py').write_text('')
            (backend / 'server.py').write_text('''\
import os
class Application:
    def __init__(self, *args, **kwargs):
        assert not any(k.startswith("INFORMATION_OS_") for k in os.environ)
    def handle(self, method, path, query, body):
        if path == "/api/jobs": return {"jobs": ["x" * 65536]}
        return {"processors": 1}
''')
            token = 'a' * 32
            messages = [{'token': token}, {'token': 'wrong', 'method': 'GET', 'path': '/api/jobs'},
                        {'token': token, 'method': 'GET', 'path': '/invalid'},
                        {'token': token, 'method': 'GET', 'path': '/api/jobs'}]
            result = subprocess.run([str(python), str(project / 'stdio_service.py'), str(root / 'data')],
                                    input=''.join(json.dumps(x) + '\n' for x in messages), text=True,
                                    capture_output=True, timeout=15, check=True,
                                    env={'PYTHONPATH': str(root), 'INFORMATION_OS_RAW_VAULT': str(root / 'outside')})
            replies = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(replies, [{'status': 'ready'}, {'error': 'unauthorized'},
                                       {'error': 'invalid operation'}, {'error': 'response too large'}])
            self.assertFalse((root / 'outside').exists())

    def test_oversized_input_fails_without_diagnostics(self):
        project = Path(__file__).resolve().parents[1]
        python = project / '.prepared/python/bin/python3'
        with tempfile.TemporaryDirectory() as root:
            process = subprocess.run([str(python), str(project / 'stdio_service.py'), root],
                                     input='x' * 65537 + '\n', text=True, capture_output=True,
                                     timeout=15, env={'PATH': '/usr/bin:/bin'})
            self.assertNotEqual(process.returncode, 0)
            self.assertEqual(process.stdout, '')
            self.assertEqual(process.stderr, '')


if __name__ == '__main__':
    unittest.main()
