#!/usr/bin/env python3
import plistlib
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class AcceptanceBuildPreservationTests(unittest.TestCase):
    def test_preserves_generated_file_on_success_and_failure(self):
        for original in (None, b"synthetic existing generated source\n"):
            for status in (0, 23):
                with self.subTest(original_exists=original is not None, status=status), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    (root / "buildscripts").mkdir()
                    shutil.copy(ROOT / "buildscripts/acceptance.sh", root / "buildscripts/acceptance.sh")
                    secret = root / "Modules/Secrets/Sources/Secrets/SecretKey.swift"
                    secret.parent.mkdir(parents=True)
                    if original is not None:
                        secret.write_bytes(original)
                        secret.chmod(0o600)
                    binary = root / "bin"
                    binary.mkdir()
                    command = binary / "xcodebuild"
                    command.write_text("#!/bin/bash\nset -eu\n"
                                       "test -z \"${FEEDLY_CLIENT_SECRET+x}\"\n"
                                       "printf 'synthetic newly generated source' > \"$FIXTURE_GENERATED_FILE\"\n"
                                       "exit \"$FIXTURE_BUILD_STATUS\"\n")
                    command.chmod(0o700)
                    environment = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ["PATH"],
                                       FEEDLY_CLIENT_SECRET="synthetic-test-value", FIXTURE_GENERATED_FILE=str(secret),
                                       FIXTURE_BUILD_STATUS=str(status))
                    result = subprocess.run(["/bin/bash", str(root / "buildscripts/acceptance.sh"), "build"],
                                            env=environment, capture_output=True)
                    self.assertEqual(result.returncode, status, result.stderr)
                    if original is None:
                        self.assertFalse(secret.exists())
                    else:
                        self.assertEqual(secret.read_bytes(), original)
                        self.assertEqual(secret.stat().st_mode & 0o777, 0o600)


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
