import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class RuntimeTest(unittest.TestCase):
    def test_prepared_runtime_works_after_relocation_without_ambient_python(self):
        source = Path(__file__).resolve().parents[1] / '.prepared' / 'python'
        self.assertTrue(source.is_dir(), 'Run ManagedEngine/prepare_runtime.sh first')
        with tempfile.TemporaryDirectory() as root:
            moved = Path(root) / 'moved runtime'
            shutil.copytree(source, moved, symlinks=True)
            process = subprocess.run([str(moved / 'bin' / 'python3'), '-I', '-c',
                                      'import sqlite3, ssl, requests, bs4, yaml, pypdf, PIL, markdown_it; print(sqlite3.sqlite_version)'],
                                     env={'PATH': '/usr/bin:/bin'}, capture_output=True,
                                     text=True, timeout=15, check=True)
            self.assertTrue(process.stdout.strip())


if __name__ == '__main__':
    unittest.main()
