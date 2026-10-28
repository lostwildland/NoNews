# T03 current-source review R10

BASE `a7136a8c3a08eb161011a3de5fe0cb4903e3bc0b`; HEAD `2ee43f01ea187aad232c5d45916e9b11f8760219`. This is an original-base review of the complete committed T03 change, excluding subsequent worker edits.

Spec reviewed all **61/61 hunks and 23/23 paths** plus controller, engine, stdio, configuration, migration, receipt, fixture and test seams. Its verdict is changes requested: **three P1s and one P2**, all source-derived and unexecuted in that review.

- **P1: controller compile blocker.** `ProcessingPreferencesViewController.swift:556` passes `completion:` to the local request helper, which accepts `onFailure:`/`then:` at line 300. Fix the call and verify the current controller with strict compilation. Historical native results do not cover the later Swift edits.
- **P1: stale credential callback can overwrite a newer service save.** At controller lines 512/527, a second full service PUT uses the earlier body even when its intent is no longer current. Save A's credential callback can run after save B and restore A's metadata. Guard the request and enforce a backend revision/expected-state condition or an equally safe scoped credential update. Add an out-of-order controller/backend regression.
- **P1: unknown mutation recovery ID is still discarded.** The outer request callback at engine lines 299/304 drops IDs for `.outcomeUnknown` returned by polling. Retain the identity until a definitive result is durably acknowledged or the user explicitly resolves it; cover failed polling and restart.
- **P2: recovery acknowledgement is shown before completion.** Controller line 139 hides the button and announces acknowledgement while its async request is still pending. The action remains enabled outside Ready. Observe the result, preserve retry on failure, and enable only in Ready.

The paired Standards verdict is pending. Its running review has not been polled or treated as clearance. The coordinator's separate [authenticated receipt identity probe](t03-receipt-identity-probe.md) independently reproduces another current-source defect; it is not a reviewer runtime rerun.

No review execution covered native build/typecheck, app/UI, Keychain, current packaged payload, live providers, keyboard, VoiceOver, appearance, narrow layout or T11 continuity. These remain acceptance gates. The original implementation owner received the findings while retaining its existing worktree and unfinished changes.
