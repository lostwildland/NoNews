# T00: Native clean-profile build and launch

Ticket: https://github.com/lostwildland/NoNews/issues/2. Starting commit: `775500c5b007c5917d46f2461544eb4ace8e21ae`.

## Reproduce on macOS

Install Xcode with its command-line tools selected, Python 3, and network access to the pinned dependencies. Engine-enabled branches also download the pinned Python runtime and dependencies. From the repository root:

```sh
# Engine-enabled branches require explicit runtime preparation before building.
if [ -f ManagedEngine/prepare_runtime.sh ]; then
  ./ManagedEngine/prepare_runtime.sh
fi
python3 buildscripts/test_acceptance.py
buildscripts/acceptance.sh build
buildscripts/acceptance.sh verify
open -n "$PWD/.build/acceptance/Build/Products/Debug/NetNewsWire.app"
```

Run the full `buildscripts/acceptance.sh test` plan only on branches with the T30 exact-current-host scripting correction and its acceptance compile flag. Older name-addressed scripting fixtures do not establish recipient isolation; use the `NetNewsWire-CI` plan, which excludes scripting, until that correction is integrated. The full-plan commands and counts below are historical evidence for their stated commits.

Always run `verify` immediately before opening the build. It verifies the code signature, bundle and app-group identifiers, and the sandbox entitlements of the app and embedded extensions. It rejects an unsigned, modified, differently identified or over-entitled app. The build uses Debug, an ad-hoc signature, and a separate sandbox and identity; it does not require `setup.sh`, a team ID, developer certificates, private API keys, or `xcbeautify`. The script copies the current source into a per-invocation private build tree, excluding generated SecretKey.swift and environment files, then clears upstream key variables before scheme generation. The original worktree is never rewritten, even during overlapping or ordinary builds. Provider features requiring those keys are unavailable. Other account services and the first-run default feeds may use the network.

The app identity is `org.nonews.acceptance.NetNewsWire-Evergreen-DEBUG`. Its app-group Info.plist value is separately named, but no app-group entitlement is granted; Debug also skips app-group access. Accounts are under `~/Library/Containers/org.nonews.acceptance.NetNewsWire-Evergreen-DEBUG/Data/Library/Application Support/NetNewsWire/Accounts`. There is no automatic import from an installed NNW container. Do not grant the app access to an existing profile through a file picker. The app uses the normal native reader and can create its own persistent acceptance data; this command does not reset it.

The test action uses `.build/acceptance-tests` for derived data, separate from the launch artifact at `.build/acceptance`; both use the same package checkout under `.build/acceptance/SourcePackages`. Xcode adds test-runner exceptions, including a read-only `/` exception, to the test host. Do not launch the test product as the acceptance app. The verifier deliberately rejects it. These tests are not an isolation proof. Build outputs and generated secrets are ignored and remain local; no cleanup command is run.

This local ad-hoc profile is not a signed CloudKit acceptance: it has no CloudKit, push or app-group entitlement and does not validate extensions, sync, production signing or release behavior. The release entitlement file and signing settings are unchanged. A real signed run requires the developer's own Apple team, matching bundle/app-group and iCloud capabilities, provisioned entitlements and account, configured outside the repository. iOS verification additionally needs an installed compatible iOS simulator runtime and device (or a provisioned physical device); it is outside this macOS entry. No team ID or signing identity is supplied here.

## Evidence, 2026-10-27

- Host: macOS 27.0.1, Xcode 27.1 (27A9275), arm64; installed compiler reports Apple Swift 6.4, while the project declares Swift 6.2. Approximately 25 GiB free before the build.
- `python3 buildscripts/test_acceptance.py`: three tests passed; synthetic signed bundles demonstrate acceptance of the isolated entitlement set and rejection of the production-style identity, absent sandbox, test-runner file exception and unsandboxed extension. Before implementation the `verify` action was absent; the first synthetic positive case also failed until the fixture used an actual signed Mach-O.
- `buildscripts/acceptance.sh build`: first attempt failed because a relative entitlement file was resolved under a Swift package directory. After changing it to an absolute path, the build passed. This was a new entry-point issue, not a proven pre-existing failure.
- No full build or test was run on the untouched baseline; there is no basis to attribute any other failure to the original revision. The initial `xcodebuild -list -project NetNewsWire.xcodeproj` was interrupted while resolving packages and is not a build result.
- `buildscripts/acceptance.sh verify`: passed on the build artifact. `codesign` showed sandbox, network client, user-selected read/write and Debug `get-task-allow` only; no application-groups or iCloud entitlement. The bundle and group values matched the identities above. The acceptance container was absent before launch.
- `open -n "$PWD/.build/acceptance/Build/Products/Debug/NetNewsWire.app"`: the process appeared and CoreGraphics reported an on-screen layer-zero window. `lsof -Fn -p <pid>` showed its open `Accounts/OnMyMac/DB.sqlite3` beneath the acceptance container. No account or article content was inspected. A first lookup immediately after launch preceded container creation; the subsequent live readback confirmed the path.
- `buildscripts/acceptance.sh test`: the final, separate-derived-data run passed the default Xcode test plan. `xcrun xcresulttool get test-results summary --path .build/acceptance-tests/Logs/Test/Test-NetNewsWire-2026.10.27_23-47-36-+0800.xcresult --format json` reported 753 passed, zero failed or skipped. An earlier run also passed 753 but put Xcode's test-host entitlements in the build directory; separation was added afterward.
- A final `buildscripts/acceptance.sh build` and `buildscripts/acceptance.sh verify` both passed. `python3 buildscripts/verify_acceptance.py .build/acceptance-tests/Build/Products/Debug/NetNewsWire.app` returned 1 as expected because the test host has additional entitlements. `bash -n buildscripts/acceptance.sh` and `git diff --cached --check` passed. The resulting launch artifact is `.build/acceptance/Build/Products/Debug/NetNewsWire.app` relative to this worktree.
- This is a launch/window and local-account-path check, not a full manual reading, Settings, extension, CloudKit or iOS journey. The installed profile was not read for a before/after comparison; isolation evidence is the signed sandbox, distinct identities and the observed acceptance database path.

## Review correction, 2026-10-28

Standards review found the acceptance build regenerated an existing ignored SecretKey source in place. The entry now saves that generated source in a private temporary directory and restores its bytes and mode on ordinary success or failure; if no file existed, the acceptance-generated file is removed. A symlink or other nonregular existing entry is refused. Release configuration is unchanged.

A public build-entry regression test uses a synthetic xcodebuild command and synthetic source bytes, never real credentials. It first failed all four existing/absent × success/failure cases, then passed after the restoration guard. The full verifier suite now passes four tests; shell syntax, diff whitespace and signature verification of the native launch artifact pass. The earlier 753-test result covers the same application source; no new app source was changed by this correction, and the full Xcode plan was not repeated. Abrupt uncatchable process termination is not a claimed restoration guarantee.

## Concurrent-build correction, 2026-10-28

Round-2 independent reviews identified a race in snapshot-and-restore of the shared generated source. That mechanism was replaced: every invocation builds a fresh source copy under .build; generation happens there, and the temporary copy is removed on normal exit. Original generated files, including concurrent ordinary-build updates, are never written or restored by the acceptance command. Untracked source changes are included; .git, .build, Python caches, generated SecretKey.swift and .env files are excluded. Prepared shipping runtime resources must live in the bundle/resource preparation location, not only an excluded development build directory.

A deterministic overlapping-build test exposes the former implementation's overwrite and passes with private source trees. It also changes the ordinary source while both builds are alive and confirms the change survives. All five verifier/build-entry test methods now pass. A fresh actual build/test and isolated launch with the new source-copy entry are requested from the original T00 implementation owner; previous 753-test evidence alone does not validate this changed build path.

## Source-copy native revalidation, 2026-10-28

Starting head `e47d0a08f61f59510dcde68cbf7a2cb409c8cb6f`, review base `775500c5b007c5917d46f2461544eb4ace8e21ae`. The first `buildscripts/acceptance.sh build` failed with `cannot find 'SecretKey' in scope`: Xcode discovers Swift package sources before the scheme pre-action generates the file. The entry now runs the existing generator in the temporary copy, with private key variables unset, before invoking Xcode; the scheme still performs its normal generation in that same copy. Synthetic build-entry checks were changed first to require generated source before Xcode starts, failed against the previous entry, and pass after the fix. `python3 buildscripts/test_acceptance.py` passes all five methods; `bash -n buildscripts/acceptance.sh` and `git diff --check` pass.

The corrected `buildscripts/acceptance.sh build` and `buildscripts/acceptance.sh verify` passed. A before/after SHA-256 check of the existing ignored generated source matched, without displaying the source; no `acceptance-source.*` directory remained after the build. Xcode used the temporary copy as its project path.

`buildscripts/acceptance.sh test` then passed. `xcrun xcresulttool get test-results summary --path .build/acceptance-tests/Logs/Test/Test-NetNewsWire-2026.10.28_00-28-19-+0800.xcresult --format json` reported 753 passed, zero failed or skipped. After the test, the generated-source SHA-256 still matched and no temporary source copies remained. `buildscripts/acceptance.sh verify` passed again; `python3 buildscripts/verify_acceptance.py .build/acceptance-tests/Build/Products/Debug/NetNewsWire.app` returned 1 for the over-entitled test host as expected.

After closing the earlier acceptance instance gracefully to avoid concurrent access to the same local account, `buildscripts/acceptance.sh verify && open -n "$PWD/.build/acceptance/Build/Products/Debug/NetNewsWire.app"` launched the newly built dedicated artifact. Process 74881 was observed running; CoreGraphics reported a layer-zero main window (1319 by 859 points), and `lsof -Fn -p 74881` showed `Accounts/OnMyMac/DB.sqlite3` under the acceptance container above. No installed account data or article content was inspected. The app was left running for native UI capture. The local build artifact is `.build/acceptance/Build/Products/Debug/NetNewsWire.app`; obtain the exact committed head with `git rev-parse HEAD` on this ticket branch.
