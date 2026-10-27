#!/bin/bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

case "${1:-}" in
  build) action=build; derived="$root/.build/acceptance" ;;
  test) action=test; derived="$root/.build/acceptance-tests" ;;
  verify) exec python3 buildscripts/verify_acceptance.py "$root/.build/acceptance/Build/Products/Debug/NetNewsWire.app" ;;
  *) echo "Usage: $0 build|test|verify" >&2; exit 2 ;;
esac

# Scheme generation must never touch an ordinary or overlapping build's source.
mkdir -p "$root/.build"
source_snapshot=$(mktemp -d "$root/.build/acceptance-source.XXXXXX")
trap 'rm -rf "$source_snapshot"' EXIT
python3 - "$root" "$source_snapshot" <<'PY'
import shutil
import sys

shutil.copytree(sys.argv[1], sys.argv[2], dirs_exist_ok=True, symlinks=True,
                ignore=shutil.ignore_patterns(".git", ".build", "__pycache__",
                                             "SecretKey.swift", ".env", ".env.*"))
PY

# Scheme pre-actions generate empty upstream keys, regardless of the caller's environment.
unset MERCURY_CLIENT_ID MERCURY_CLIENT_SECRET FEEDLY_CLIENT_ID FEEDLY_CLIENT_SECRET INOREADER_APP_ID INOREADER_APP_KEY

# SwiftPM discovers source files before the scheme's generation pre-action runs.
PROJECT_DIR="$source_snapshot" "$source_snapshot/buildscripts/updateSecrets.sh"

xcodebuild -project "$source_snapshot/NetNewsWire.xcodeproj" -scheme NetNewsWire -configuration Debug \
  -destination 'platform=macOS' -derivedDataPath "$derived" \
  -clonedSourcePackagesDirPath "$root/.build/acceptance/SourcePackages" \
  CLANG_MODULE_CACHE_PATH="$source_snapshot/.module-cache" \
  ORGANIZATION_IDENTIFIER=org.nonews.acceptance DEVELOPMENT_TEAM= CODE_SIGN_IDENTITY=- \
  CODE_SIGN_STYLE=Manual CODE_SIGN_ENTITLEMENTS="$source_snapshot/buildscripts/acceptance.entitlements" \
  "$action"
