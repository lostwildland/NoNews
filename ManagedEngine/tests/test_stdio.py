import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest
import sys


class ManagedServiceTest(unittest.TestCase):
    def test_boundary_sized_escaped_request_preserves_service(self):
        script = Path(__file__).resolve().parents[1] / 'stdio_service.py'
        token = 'a' * 32
        with tempfile.TemporaryDirectory() as root:
            requests = [
                {'token': token},
                {'id': 1, 'token': token, 'method': 'GET', 'path': '/api/status',
                 'body': {'text': '\u0001' * 199996 + '😀'}},
                {'id': 2, 'token': token, 'method': 'GET', 'path': '/api/settings/processing'},
            ]
            process = subprocess.run([sys.executable, str(script), root],
                                     input=''.join(json.dumps(x) + '\n' for x in requests),
                                     text=True, capture_output=True, timeout=30,
                                     env={'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'})
            self.assertEqual(process.returncode, 0, process.stderr)
            replies = [json.loads(line) for line in process.stdout.splitlines()]
            self.assertEqual(replies[1]['result']['schemaVersion'], 41)
            self.assertEqual(replies[2]['result']['processors'], 1)

    @unittest.skipUnless(os.environ.get('IO_TEST_PYTHON') and os.environ.get('IO_TEST_SOURCE'),
                         'Optional reference-source comparison')
    def test_real_service_settings_survive_restart(self):
        python = os.environ['IO_TEST_PYTHON']
        source = os.environ['IO_TEST_SOURCE']
        script = Path(__file__).resolve().parents[1] / 'stdio_service.py'
        with tempfile.TemporaryDirectory() as root:
            isolated_script = Path(root) / "stdio_service.py"
            shutil.copy2(script, isolated_script)
            def session(requests):
                environment = {'PYTHONPATH': source, 'PYTHONDONTWRITEBYTECODE': '1'}
                process = subprocess.run([python, str(isolated_script), root], input='\n'.join(map(json.dumps, requests)) + '\n',
                                         text=True, capture_output=True, env=environment, timeout=30, check=True)
                return [json.loads(line) for line in process.stdout.splitlines()]
            token = 'a' * 32
            bootstrap = {'token': token}
            first = session([bootstrap, {'token': 'wrong', 'method': 'GET', 'path': '/api/jobs'},
                             {'token': 'é', 'method': 'GET', 'path': '/api/jobs'},
                             {'token': token, 'method': 'GET', 'path': '/api/unknown'},
                             {'token': token, 'method': [], 'path': '/api/jobs'},
                             {'token': token, 'method': 'GET', 'path': '/api/jobs'},
                             {'token': token, 'method': 'PUT', 'path': '/api/settings/processing', 'body': {'processors': 3}}])
            self.assertEqual(first[0]['status'], 'ready')
            self.assertEqual(first[1]['error'], 'unauthorized')
            self.assertEqual(first[2]['error'], 'unauthorized')
            self.assertEqual(first[3]['error'], 'invalid operation')
            self.assertEqual(first[4]['error'], 'invalid operation')
            self.assertEqual(first[5]['result']['jobs'], [])
            self.assertEqual(first[6]['result']['processors'], 3)
            second = session([bootstrap, {'token': token, 'method': 'GET', 'path': '/api/settings/processing'}])
            self.assertEqual(second[1]['result']['processors'], 3)


if __name__ == '__main__':
    unittest.main()
