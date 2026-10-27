#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/nonews-controller.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT
"$root/ManagedEngine/.prepared/python/bin/python3" -B "$root/ManagedEngine/tests/make_large_fixture.py" "$root/ManagedEngine/.prepared" "$tmp/data"
"$root/ManagedEngine/.prepared/python/bin/python3" -B - "$root/ManagedEngine/.prepared" "$tmp/rejected" <<'PYTEST'
import sys,sqlite3
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from backend.server import Application
root=Path(sys.argv[2]); Application(root/'information.sqlite',root/'raw',root/'artifacts',token='a'*32,write_scope='settings')
with sqlite3.connect(root/'information.sqlite') as db:
 db.execute("CREATE TRIGGER reject_setting BEFORE INSERT ON app_settings BEGIN SELECT RAISE(ABORT,'denied'); END")
PYTEST
swiftc -swift-version 6 -D DEBUG "$root/Mac/Processing/ProcessingEngine.swift" "$root/ManagedEngine/tests/ProcessingEngineChecks.swift" -o "$tmp/controller-check"
"$tmp/controller-check" "$root" "$tmp/data" "$tmp/rejected"
