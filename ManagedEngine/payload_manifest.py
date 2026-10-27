"""Create or verify the exact files and contained symlinks in a payload."""
import hashlib
import json
from pathlib import Path
import sys


def contents(root):
    entries = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root).as_posix()
        if relative == 'PAYLOAD-MANIFEST.json':
            continue
        if path.is_symlink():
            target = path.readlink()
            resolved = (path.parent / target).resolve()
            if target.is_absolute() or not resolved.is_relative_to(root) or not resolved.exists():
                raise ValueError('Payload contains an external or broken symlink')
            entries[relative] = {'link': str(target)}
        elif path.is_file():
            entries[relative] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    return entries


def main():
    root = Path(sys.argv[2]).resolve()
    manifest = root / 'PAYLOAD-MANIFEST.json'
    actual = contents(root)
    if sys.argv[1] == 'write':
        manifest.write_text(json.dumps(actual, sort_keys=True, separators=(',', ':')) + '\n')
    elif sys.argv[1] == 'check':
        if actual != json.loads(manifest.read_text()):
            raise ValueError('Payload integrity check failed')
    else:
        raise ValueError('Unknown action')


if __name__ == '__main__':
    main()
