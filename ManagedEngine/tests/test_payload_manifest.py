from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class PayloadManifestTest(unittest.TestCase):
    def test_rejects_extra_files_and_external_symlinks(self):
        script = Path(__file__).resolve().parents[1] / 'payload_manifest.py'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'payload'
            root.mkdir()
            (root / 'file').write_text('known')
            def run(action):
                return subprocess.run([sys.executable, str(script), action, str(root)], capture_output=True)
            self.assertEqual(run('write').returncode, 0)
            self.assertEqual(run('check').returncode, 0)
            (root / 'extra').write_text('unknown')
            self.assertNotEqual(run('check').returncode, 0)
            (root / 'extra').unlink()
            (root / 'link').symlink_to(Path(tmp))
            self.assertNotEqual(run('write').returncode, 0)

    def test_staged_source_matches_checkout(self):
        engine = Path(__file__).resolve().parents[1]
        subprocess.run([sys.executable, str(engine / 'verify_payload_source.py'), str(engine / '.prepared')], check=True)
