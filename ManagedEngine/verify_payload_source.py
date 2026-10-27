"""Refuse to embed a prepared payload that differs from the checked-out source."""
from pathlib import Path
import sys
from payload_sources import BACKEND_SOURCES, ROOT_SOURCES

source = Path(__file__).resolve().parent
payload = Path(sys.argv[1]).resolve()
expected = {f'backend/{name}': source / 'backend' / name for name in BACKEND_SOURCES}
expected.update({name: source / name for name in ROOT_SOURCES})
backend = payload / 'backend'
if backend.is_symlink() or not backend.is_dir() or {path.name for path in backend.iterdir()} != set(BACKEND_SOURCES):
    raise SystemExit('Prepared backend differs from source; prepare the payload again.')
if (source / 'backend').is_symlink():
    raise SystemExit('Declared payload source must be a regular file.')
for name, path in expected.items():
    staged = payload / name
    if path.is_symlink() or not path.is_file() or staged.is_symlink() or not staged.is_file() or staged.read_bytes() != path.read_bytes():
        raise SystemExit('Prepared source differs from checkout; prepare the payload again.')
