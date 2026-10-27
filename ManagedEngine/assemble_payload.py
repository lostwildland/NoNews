"""Add managed IO source and an integrity manifest to a prepared runtime."""
from pathlib import Path
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from payload_manifest import contents
from payload_sources import BACKEND_SOURCES, ROOT_SOURCES
import json

source = Path(__file__).resolve().parent
payload = Path(sys.argv[1]).resolve()
expected = {f'backend/{name}': source / 'backend' / name for name in BACKEND_SOURCES}
expected.update({name: source / name for name in ROOT_SOURCES})
if (source / 'backend').is_symlink() or any(path.is_symlink() or not path.is_file() for path in expected.values()):
    raise SystemExit('Declared payload source must be a regular file.')
(payload / 'backend').mkdir()
for name, path in expected.items():
    shutil.copy2(path, payload / name)
for cache in payload.rglob('__pycache__'):
    if cache.is_dir() and not cache.is_symlink():
        shutil.rmtree(cache)
for bytecode in payload.rglob('*.pyc'):
    if bytecode.is_file() and not bytecode.is_symlink():
        bytecode.unlink()
manifest = payload / 'PAYLOAD-MANIFEST.json'
manifest.write_text(json.dumps(contents(payload), sort_keys=True, separators=(',', ':')) + '\n')
