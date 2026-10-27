#!/usr/bin/env python3
import plistlib
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class AcceptanceVerificationTests(unittest.TestCase):
    def make_app(self, directory, *, identity="org.nonews.acceptance.NetNewsWire-Evergreen-DEBUG", sandbox=True):
        app = Path(directory) / "Fixture.app"
        contents = app / "Contents"
        executable = contents / "MacOS/Fixture"
        executable.parent.mkdir(parents=True)
        subprocess.run(["clang", "-x", "c", "-o", str(executable), "-"], input=b"int main(void) { return 0; }\n", check=True, capture_output=True)
        with (contents / "Info.plist").open("wb") as file:
            plistlib.dump({"CFBundleIdentifier": identity, "CFBundleExecutable": "Fixture", "AppGroup": "group.org.nonews.acceptance.NetNewsWire-Evergreen-DEBUG"}, file)
        entitlements = ROOT / "buildscripts/acceptance.entitlements" if sandbox else Path(directory) / "empty.plist"
        if not sandbox:
            with entitlements.open("wb") as file:
                plistlib.dump({}, file)
        subprocess.run(["codesign", "--force", "--sign", "-", "--entitlements", str(entitlements), str(app)], check=True, capture_output=True)
        return app

    def verify(self, app):
        return subprocess.run(["python3", str(ROOT / "buildscripts/verify_acceptance.py"), str(app)], capture_output=True)

    def test_accepts_isolated_sandbox_and_rejects_other_identity_or_missing_sandbox(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(self.verify(self.make_app(directory)).returncode, 0)
        with tempfile.TemporaryDirectory() as directory:
            self.assertNotEqual(self.verify(self.make_app(directory, identity="com.ranchero.NetNewsWire-Evergreen")).returncode, 0)
        with tempfile.TemporaryDirectory() as directory:
            self.assertNotEqual(self.verify(self.make_app(directory, sandbox=False)).returncode, 0)

    def test_rejects_test_runner_file_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            app = self.make_app(directory)
            entitlements = Path(directory) / "test-host.plist"
            with (ROOT / "buildscripts/acceptance.entitlements").open("rb") as file:
                values = plistlib.load(file)
            values["com.apple.security.temporary-exception.files.absolute-path.read-only"] = ["/"]
            with entitlements.open("wb") as file:
                plistlib.dump(values, file)
            subprocess.run(["codesign", "--force", "--sign", "-", "--entitlements", str(entitlements), str(app)], check=True, capture_output=True)
            self.assertNotEqual(self.verify(app).returncode, 0)

    def test_rejects_an_unsandboxed_embedded_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            app = self.make_app(directory)
            plugins = app / "Contents/PlugIns"
            plugins.mkdir()
            self.make_app(plugins, sandbox=False).rename(plugins / "Fixture.appex")
            (plugins / "empty.plist").unlink()
            subprocess.run(["codesign", "--force", "--sign", "-", "--entitlements", str(ROOT / "buildscripts/acceptance.entitlements"), str(app)], check=True, capture_output=True)
            self.assertNotEqual(self.verify(app).returncode, 0)


if __name__ == "__main__":
    unittest.main()
