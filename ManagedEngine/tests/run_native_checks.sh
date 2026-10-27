#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/nonews-controller.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT
"$root/ManagedEngine/.prepared/python/bin/python3" -B "$root/ManagedEngine/tests/make_large_fixture.py" "$root/ManagedEngine/.prepared" "$tmp/data"
swiftc -swift-version 6 -D DEBUG "$root/Mac/Processing/ProcessingEngine.swift" "$root/ManagedEngine/tests/ProcessingEngineChecks.swift" -o "$tmp/controller-check"
"$tmp/controller-check" "$root" "$tmp/data"
