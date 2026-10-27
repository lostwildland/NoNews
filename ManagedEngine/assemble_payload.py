"""Add managed IO source and an integrity manifest to a prepared runtime."""
from pathlib import Path
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from payload_manifest import contents
import json

source = Path(__file__).resolve().parent
payload = Path(sys.argv[1]).resolve()
shutil.copytree(source / 'backend', payload / 'backend', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
for name in ('stdio_service.py', 'PROVENANCE.md', 'requirements.lock'):
    shutil.copy2(source / name, payload / name)
for cache in payload.rglob('__pycache__'):
    if cache.is_dir() and not cache.is_symlink():
        shutil.rmtree(cache)
for bytecode in payload.rglob('*.pyc'):
    if bytecode.is_file() and not bytecode.is_symlink():
        bytecode.unlink()
manifest = payload / 'PAYLOAD-MANIFEST.json'
manifest.write_text(json.dumps(contents(payload), sort_keys=True, separators=(',', ':')) + '\n')
