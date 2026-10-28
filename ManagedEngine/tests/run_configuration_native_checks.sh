#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/nonews-config-check.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT
swiftc -swift-version 6 -D DEBUG "$root/Mac/Processing/ProcessingEngine.swift" "$root/ManagedEngine/tests/ProcessingConfigurationChecks.swift" -o "$tmp/check"
"$tmp/check" "$root"
