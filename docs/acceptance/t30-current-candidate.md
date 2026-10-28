# T30 native fixture and cancellation candidate

Original base `2782c51bae6f68a91baa6b86c88cc0c5fe5a1cb2`; current source is `e44f338`, after the reviewed R17 source/evidence pair, shared-helper correction `9ab2069`, and correction `b33a201`. The [coverage ledger](t30-review-coverage.json) still pins the earlier106-path connected candidate; the new seven-path `b33a201...e44f338` delta is tracked separately until fresh R21 review completes. This candidate remains the fixture/cancellation prerequisite; it does not satisfy full ticket30 parity, migration, sync or release acceptance.

## Current evidence

The current-source acceptance plan at `e44f338` passed 827 top-level tests with zero failures/skips; the result is `Test-NetNewsWire-2026.10.28_17-49-19-+0800.xcresult`, with 300 dynamic parameter runs and one existing generic main-thread warning. The focused SyncDatabase transaction regression passed within that plan. This is macOS fixture evidence only: no real CloudKit server token, live sync, final artifact, iOS runtime or production deletion is established.

Source/native ownership is released. The complete65be895...51d169e connected correction changes19 paths (671 additions/229 deletions); R18 found two P1 data-integrity risks and the shared-helper correction adds an unreviewed four-path delta. Fresh R19 rechecks are required before further acceptance. T03 has the standalone native/component grant after its P1 source is ready; no simultaneous full/native run is authorized.

The earlier partiala85ac89 result remains208 passed, zero failures/skips,208 total in15:25:17xcresult, independently read by root. Its owner-reported DELETE commit/receive/admission proof did not cover the remaining update/status and callback/admission red gaps. The newer source and reported schedules above supersede that implementation checkpoint; neither result is a final full/build/iOS run.

Root independently read the12:40:25 xcresult summary:203 passed, zero failures/skips,203 total. The owner reports this combined working-source run includes failed article deletion, withheld CloudKit page checkpoint and retained pending sync status. The adapted baseline red and widget fetch/encode/write failure results are owner evidence in the worker's native-fixture record; root has not rerun them.

The historical full-plan result remains791 passes at5013c91. Its independently exported action had zero disk-I/O/vnode-unlink matches. It predates the current consumer/provider/CloudKit fixes. No current-source full Mac plan, normal signed artifact or final generic iOS build is established by that result. Final heavy runs remain deferred until known review findings stabilize.

## Review frontier

Fresh R20 source review of `b33a201` found one release-compile P1 plus FTS iteration, CloudKit caller, and selection-transaction P2s. The seven-path correction is now at `e44f338`; paired R21 Standards/Spec rechecks are running and must clear it before acceptance.

The interrupted R16 runs produced no verdict. Fresh [paired R17 reviews](t30-page-delete-review-r17.md) covered all eight changed-hunk sets at65be895: Standards reported no material Standards finding and separately one Spec P1; Spec reported two P1s (transaction durability and dropped individual record errors). These source-derived findings require correction and behavioral proof. Root's one-line receive-error result correction has parsing proof only; the additional admission-lock assessment remains open. Other review scopes below remain open.

- Page application, token/checkpoint advancement, pending sync status and the new failed SQL delete path, including shared CloudKit callback admission.
- Per-operation send/receive/notification context and controlled queue/selection failure.
- Status command outcomes, partial account success and undo/redo; timeline failure/supersession; widget atomic publication and icon preservation.
- Local refresh overlap and matching callbacks; Feedbin conditional-GET acknowledgement after successful reconciliation; incomplete earlier Feedly/ReaderAPI send/error/rollback coverage.
- Remaining account fixture, storage test and exact-host scripting/build harness coverage, followed by a connected assessment of the complete current API.

Prior verdicts apply only to their stated blobs and seams. Earlier incomplete reviews are not upgraded, and changed/new files are pending. The candidate includes a new deletion correction discovered while testing; it must be reviewed with its queue error propagation and page commit caller, rather than inferred safe from a green count.

After source review clears, the original owner must run final focused checks as needed, exact-host scripting binding before the full Mac plan, action-log diagnostics, a normal isolated acceptance build and strict signature/identity checks, and the appropriate generic iOS build from the same final source. Live-provider, device, production account deletion, personal migration and visible UI remain separate unverified requirements.
