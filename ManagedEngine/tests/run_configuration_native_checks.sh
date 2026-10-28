#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/nonews-config-check.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT
"$root/ManagedEngine/.prepared/python/bin/python3" -B "$root/ManagedEngine/verify_payload_source.py" "$root/ManagedEngine/.prepared"
"$root/ManagedEngine/.prepared/python/bin/python3" -B "$root/ManagedEngine/payload_manifest.py" check "$root/ManagedEngine/.prepared"
swiftc -swift-version 6 -D DEBUG -module-cache-path "$tmp/module-cache" "$root/Mac/Processing/ProcessingEngine.swift" "$root/ManagedEngine/tests/ProcessingConfigurationChecks.swift" -o "$tmp/check"
"$tmp/check" "$root"
