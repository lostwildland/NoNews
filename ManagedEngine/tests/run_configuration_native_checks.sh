#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/nonews-config-check.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT
products="${NONEWS_T02_DEBUG_PRODUCTS:-}"
if [[ -z "$products" ]]; then
	echo "set NONEWS_T02_DEBUG_PRODUCTS to the accepted T02 Debug products directory" >&2
	exit 2
fi
for artifact in Secrets.o ErrorLog.o RSCore.o RSDatabase.o RSDatabaseObjC.o RSCoreObjC.o; do
	if [[ ! -f "$products/$artifact" ]]; then
		echo "accepted T02 Debug product is missing: $products/$artifact" >&2
		exit 2
	fi
done
# Source checks use the existing interpreter with current checkout entry points.
# Packaged acceptance additionally requires an exact, freshly prepared payload.
if [[ "${NONEWS_CHECK_PACKAGED:-0}" == 1 ]]; then
	"$root/ManagedEngine/.prepared/python/bin/python3" -B "$root/ManagedEngine/verify_payload_source.py" "$root/ManagedEngine/.prepared"
	"$root/ManagedEngine/.prepared/python/bin/python3" -B "$root/ManagedEngine/payload_manifest.py" check "$root/ManagedEngine/.prepared"
fi
swiftc -warnings-as-errors -swift-version 6 -D DEBUG -target arm64-apple-macos15.0 \
	-module-cache-path "$tmp/module-cache" "$root/Mac/Processing/ProcessingEngine.swift" \
	"$root/ManagedEngine/tests/ProcessingConfigurationChecks.swift" -o "$tmp/check"
"$tmp/check" "$root"
cat > "$tmp/RSCoreObjC.modulemap" <<EOF
module RSCoreObjC {
  umbrella header "$root/Modules/RSCore/Sources/RSCoreObjC/include/RSCore.h"
  export *
}
EOF
cat > "$tmp/RSDatabaseObjC.modulemap" <<EOF
module RSDatabaseObjC {
  umbrella header "$root/Modules/RSDatabase/Sources/RSDatabaseObjC/include/RSDatabaseObjC.h"
  export *
}
EOF
xcrun swiftc -warnings-as-errors -swift-version 6 -D DEBUG -target arm64-apple-macos15.0 \
	-I "$products" -F "$products" -L "$products" -module-cache-path "$tmp/preferences-module-cache" \
	-Xcc -fmodule-map-file="$tmp/RSCoreObjC.modulemap" \
	-Xcc -fmodule-map-file="$tmp/RSDatabaseObjC.modulemap" \
	"$root/Mac/Processing/ProcessingEngine.swift" \
	"$root/Mac/Preferences/ProcessingPreferencesViewController.swift" \
	"$root/ManagedEngine/tests/PreferencesControllerChecks.swift" \
	"$products/Secrets.o" "$products/ErrorLog.o" "$products/RSCore.o" \
	"$products/RSDatabase.o" "$products/RSDatabaseObjC.o" "$products/RSCoreObjC.o" \
	-framework AppKit -framework Security -o "$tmp/preferences-check"
"$tmp/preferences-check" "$root"
