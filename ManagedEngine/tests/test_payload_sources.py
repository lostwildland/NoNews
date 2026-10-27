import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
from payload_sources import BACKEND_SOURCES, ROOT_SOURCES


class PayloadSourceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        for name in ('assemble_payload.py', 'verify_payload_source.py',
                     'payload_manifest.py', 'payload_sources.py'):
            shutil.copy2(ENGINE / name, self.source / name)
        backend = self.source / 'backend'
        backend.mkdir()
        for name in BACKEND_SOURCES:
            (backend / name).write_text('# Synthetic public source: ' + name + '\n')
        for name in ROOT_SOURCES:
            (self.source / name).write_text('Synthetic public resource: ' + name + '\n')
        self.payload = self.root / 'payload'
        self.payload.mkdir()
        (self.payload / 'python').mkdir()

    def run_script(self, name, *args):
        return subprocess.run([sys.executable, str(self.source / name), *map(str, args)],
                              capture_output=True, text=True, timeout=10)

    def assemble(self):
        result = self.run_script('assemble_payload.py', self.payload)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_private_source_files_are_not_distributed(self):
        (self.source / 'backend/.env').write_text('SYNTHETIC_PRIVATE_ENV=sentinel')
        (self.source / 'backend/personal.py').write_text('SYNTHETIC_PRIVATE_CODE = True')
        self.assemble()
        actual = {path.name for path in (self.payload / 'backend').iterdir()}
        self.assertEqual(actual, set(BACKEND_SOURCES))
        self.assertIn('server.py', actual)
        self.assertIn('schema_semantics.py', actual)
        manifest = json.loads((self.payload / 'PAYLOAD-MANIFEST.json').read_text())
        self.assertNotIn('backend/.env', manifest)
        self.assertNotIn('backend/personal.py', manifest)
        self.assertEqual(self.run_script('verify_payload_source.py', self.payload).returncode, 0)

    def test_extra_staged_files_are_refused_even_with_matching_manifest(self):
        self.assemble()
        for name in ('.env', 'personal.py'):
            with self.subTest(name=name):
                extra = self.payload / 'backend' / name
                extra.write_text('Synthetic unapproved bytes')
                self.assertEqual(self.run_script('payload_manifest.py', 'write', self.payload).returncode, 0)
                self.assertEqual(self.run_script('payload_manifest.py', 'check', self.payload).returncode, 0)
                self.assertNotEqual(self.run_script('verify_payload_source.py', self.payload).returncode, 0)
                extra.unlink()

    def test_declared_source_symlink_is_refused_before_manifest_publication(self):
        private = self.root / 'private.py'
        private.write_text('Synthetic private sentinel')
        source = self.source / 'backend/server.py'
        source.unlink()
        source.symlink_to(private)
        self.assertNotEqual(self.run_script('assemble_payload.py', self.payload).returncode, 0)
        self.assertFalse((self.payload / 'PAYLOAD-MANIFEST.json').exists())

    def test_extra_staged_root_files_are_refused_after_manifest_rewrite(self):
        self.assemble()
        for name in ('.env', 'local-config.json'):
            with self.subTest(name=name):
                extra = self.payload / name
                extra.write_text('Synthetic private root bytes')
                self.assertEqual(self.run_script('payload_manifest.py', 'write', self.payload).returncode, 0)
                self.assertEqual(self.run_script('payload_manifest.py', 'check', self.payload).returncode, 0)
                self.assertNotEqual(self.run_script('verify_payload_source.py', self.payload).returncode, 0)
                extra.unlink()

    def test_backend_directory_symlink_is_refused(self):
        self.assemble()
        backend = self.payload / 'backend'
        moved = self.root / 'moved-backend'
        backend.rename(moved)
        backend.symlink_to(moved, target_is_directory=True)
        self.assertNotEqual(self.run_script('verify_payload_source.py', self.payload).returncode, 0)
