#!/bin/bash
set -euo pipefail
payload="$SRCROOT/ManagedEngine/.prepared"
destination="$TARGET_BUILD_DIR/$UNLOCALIZED_RESOURCES_FOLDER_PATH/ProcessingEngine"
if [ ! -x "$payload/python/bin/python3" ] || [ ! -f "$payload/stdio_service.py" ] || [ ! -f "$payload/PAYLOAD-MANIFEST.json" ]; then
  echo 'error: Processing payload is missing. Run ManagedEngine/prepare_runtime.sh before building.' >&2
  exit 1
fi
python3 "$SRCROOT/ManagedEngine/payload_manifest.py" check "$payload" || { echo 'error: Processing payload integrity check failed.' >&2; exit 1; }
python3 "$SRCROOT/ManagedEngine/verify_payload_source.py" "$payload" || { echo 'error: Processing payload does not match source.' >&2; exit 1; }
for arch in ${ARCHS:-}; do
  if ! lipo -verify_arch "$arch" "$payload/python/bin/python3"; then
    echo "error: Processing runtime does not support build architecture $arch." >&2
    exit 1
  fi
done
if [ -z "${EXPANDED_CODE_SIGN_IDENTITY:-}" ]; then
  echo 'error: Processing payload requires a signing identity.' >&2
  exit 1
fi
python3 - "$destination" <<'PY'
from pathlib import Path
import shutil, sys
path = Path(sys.argv[1])
if path.exists():
    shutil.rmtree(path)
PY
mkdir -p "$destination"
ditto "$payload" "$destination"
while IFS= read -r -d '' binary; do
  if [[ "$binary" == */bin/python3.13 ]]; then
    codesign --force --sign "$EXPANDED_CODE_SIGN_IDENTITY" --options runtime --entitlements "$SRCROOT/buildscripts/processing-engine.entitlements" "$binary"
  else
    codesign --force --sign "$EXPANDED_CODE_SIGN_IDENTITY" --options runtime "$binary"
  fi
done < <(find "$destination/python" -type f \( -name '*.so' -o -name '*.dylib' -o -name 'python3.13' \) -print0)
