"""Refuse to embed a prepared payload that differs from the checked-out source."""
from pathlib import Path
import sys

source = Path(__file__).resolve().parent
payload = Path(sys.argv[1]).resolve()
expected = {p.relative_to(source).as_posix(): p for p in (source / 'backend').rglob('*.py')}
expected.update({name: source / name for name in ('stdio_service.py', 'PROVENANCE.md', 'JOBS-IPC.md', 'requirements.lock')})
actual = {p.relative_to(payload).as_posix() for p in (payload / 'backend').rglob('*.py')}
if actual != {name for name in expected if name.startswith('backend/')}:
    raise SystemExit('Prepared backend differs from source; prepare the payload again.')
for name, path in expected.items():
    staged = payload / name
    if staged.is_symlink() or not staged.is_file() or staged.read_bytes() != path.read_bytes():
        raise SystemExit('Prepared source differs from checkout; prepare the payload again.')
