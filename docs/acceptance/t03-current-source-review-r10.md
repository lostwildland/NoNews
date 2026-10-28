# T03 current-source review R10

BASE `a7136a8c3a08eb161011a3de5fe0cb4903e3bc0b`; HEAD `2ee43f01ea187aad232c5d45916e9b11f8760219`. This is an original-base review of the complete committed T03 change, excluding subsequent worker edits.

Spec reviewed all **61/61 hunks and 23/23 paths** plus controller, engine, stdio, configuration, migration, receipt, fixture and test seams. Its verdict is changes requested: **three P1s and one P2**, all source-derived and unexecuted in that review.

- **P1: controller compile blocker.** `ProcessingPreferencesViewController.swift:556` passes `completion:` to the local request helper, which accepts `onFailure:`/`then:` at line 300. Fix the call and verify the current controller with strict compilation. Historical native results do not cover the later Swift edits.
- **P1: stale credential callback can overwrite a newer service save.** At controller lines 512/527, a second full service PUT uses the earlier body even when its intent is no longer current. Save A's credential callback can run after save B and restore A's metadata. Guard the request and enforce a backend revision/expected-state condition or an equally safe scoped credential update. Add an out-of-order controller/backend regression.
- **P1: unknown mutation recovery ID is still discarded.** The outer request callback at engine lines 299/304 drops IDs for `.outcomeUnknown` returned by polling. Retain the identity until a definitive result is durably acknowledged or the user explicitly resolves it; cover failed polling and restart.
- **P2: recovery acknowledgement is shown before completion.** Controller line 139 hides the button and announces acknowledgement while its async request is still pending. The action remains enabled outside Ready. Observe the result, preserve retry on failure, and enable only in Ready.

The paired Standards verdict is pending. Its running review has not been polled or treated as clearance. The coordinator's separate [authenticated receipt identity probe](t03-receipt-identity-probe.md) independently reproduces another current-source defect; it is not a reviewer runtime rerun.

No review execution covered native build/typecheck, app/UI, Keychain, current packaged payload, live providers, keyboard, VoiceOver, appearance, narrow layout or T11 continuity. These remain acceptance gates. The original implementation owner received the findings while retaining its existing worktree and unfinished changes.

## Coordinator credential-order probe

The coordinator independently exercised the backend consequence of the stale credential callback at exact `2ee43f0`, using the extracted committed service, authenticated stdio and a temporary synthetic profile. Three mutations were separately queued and polled to durable completion:

1. Save OpenAI-compatible service A.
2. Save newer name/endpoint B for the same ID; public readback confirms B.
3. Submit A's captured full service body with `credentialState: verified`, matching the request emitted by the reviewed late callback.

Public readback after step 3 contains A's name and endpoint, and claims verified. B was overwritten. EOF exited `0` and the temporary profile/source were removed. No provider request, Keychain access or AppKit controller ran. This reproduces the backend loss under the ordered request schedule; the actual native callback race remains source-derived until its wiring regression executes. The owner received this evidence and the requested expected-state/credential-update regression.

## Native check entry

At `2ee43f0`, `ManagedEngine/tests/run_configuration_native_checks.sh` verifies the payload and compiles `ProcessingEngine.swift` with `ProcessingConfigurationChecks.swift`. It does not compile the Preferences controller or `PreferencesControllerChecks.swift`. Fixed-object search in `.github`, `buildscripts` and `ManagedEngine/tests` finds the controller check's declaration but no invocation; its execution is recorded only as a historical manual command in the worker evidence.

The separate full app build would compile the controller when run. The standalone configuration command alone does not, so its success cannot clear later Preferences edits. The owner is to connect strict controller compilation and wiring execution to the reproducible native validation entry, preserving its declared dependencies and avoiding reliance on an undocumented `/tmp` executable. No workflow or worker source was changed by this coordinator audit.
