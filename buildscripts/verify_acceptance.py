#!/usr/bin/env python3
"""Reject an acceptance app unless its signed identity and sandbox are isolated."""

import plistlib
import subprocess
import sys
from pathlib import Path


def main(app: Path) -> None:
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
    with (app / "Contents/Info.plist").open("rb") as file:
        info = plistlib.load(file)
    if info.get("CFBundleIdentifier") != "org.nonews.acceptance.NetNewsWire-Evergreen-DEBUG":
        raise ValueError("unexpected bundle identity")
    if info.get("AppGroup") != "group.org.nonews.acceptance.NetNewsWire-Evergreen-DEBUG":
        raise ValueError("unexpected app group identity")
    for executable in [app, *(app / "Contents/PlugIns").glob("*.appex")]:
        result = subprocess.run(["codesign", "-d", "--entitlements", ":-", str(executable)], check=True, capture_output=True)
        entitlements = plistlib.loads(result.stdout)
        entitlements.pop("com.apple.security.get-task-allow", None)
        if entitlements != {
            "com.apple.security.app-sandbox": True,
            "com.apple.security.network.client": True,
            "com.apple.security.files.user-selected.read-write": True,
        }:
            raise ValueError(f"unexpected sandbox entitlements: {executable.name}")
    print(f"Verified isolated sandbox identity: {app}")


if __name__ == "__main__":
    try:
        main(Path(sys.argv[1]))
    except (IndexError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Acceptance verification failed: {error}", file=sys.stderr)
        sys.exit(1)
