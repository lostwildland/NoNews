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

# The shared scheme regenerates this source; acceptance must leave it unchanged.
generated="$root/Modules/Secrets/Sources/Secrets/SecretKey.swift"
if [[ -L "$generated" || ( -e "$generated" && ! -f "$generated" ) ]]; then
  echo "Acceptance requires a regular generated source file." >&2
  exit 2
fi
saved=$(mktemp -d "${TMPDIR:-/tmp}/nonews-acceptance.XXXXXX")
if [[ -f "$generated" ]]; then
  if ! cp -p "$generated" "$saved/SecretKey.swift"; then
    rm -f "$saved/SecretKey.swift"
    rmdir "$saved"
    exit 1
  fi
fi
restore_generated_source() {
  result=$?
  trap - EXIT
  if [[ -f "$saved/SecretKey.swift" ]]; then
    cp -p "$saved/SecretKey.swift" "$generated"
    rm "$saved/SecretKey.swift"
  else
    rm -f "$generated"
  fi
  rmdir "$saved"
  exit "$result"
}
trap restore_generated_source EXIT

# Scheme pre-actions generate empty upstream keys, regardless of the caller's environment.
unset MERCURY_CLIENT_ID MERCURY_CLIENT_SECRET FEEDLY_CLIENT_ID FEEDLY_CLIENT_SECRET INOREADER_APP_ID INOREADER_APP_KEY

xcodebuild -project NetNewsWire.xcodeproj -scheme NetNewsWire -configuration Debug \
  -destination 'platform=macOS' -derivedDataPath "$derived" \
  -clonedSourcePackagesDirPath "$root/.build/acceptance/SourcePackages" \
  ORGANIZATION_IDENTIFIER=org.nonews.acceptance DEVELOPMENT_TEAM= CODE_SIGN_IDENTITY=- \
  CODE_SIGN_STYLE=Manual CODE_SIGN_ENTITLEMENTS="$root/buildscripts/acceptance.entitlements" \
  "$action"
