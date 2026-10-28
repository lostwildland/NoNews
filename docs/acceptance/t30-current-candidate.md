# T30 native fixture and cancellation candidate

Original base `2782c51bae6f68a91baa6b86c88cc0c5fe5a1cb2`; current partial R17 checkpoint `a85ac897758debe408b5a08e616fc97836966a2d`, following reviewed65be895 and coordinator receive-error correction926bbe3. The [coverage ledger](t30-review-coverage.json) now pins106 logical changed paths, including the additional feed-settings read test. This candidate is the fixture/cancellation prerequisite; it does not satisfy full ticket30 parity, migration, sync or release acceptance.

## Current evidence

Root independently read the15:25:17 xcresult:208 passed, zero failures/skips,208 total. The owner reports actual deferred-constraint DELETE commit red/green, retained article/pending status/withheld page and continued database use; queued receive and feed-settings admission green also passed. Root has not independently reproduced these schedules. The owner explicitly leaves other update/status callbacks before commit, successful callback-token recovery/exact incomplete-page red, and prior-lock behavioral red unfinished. Same ownerR21 continues this connected correction with the focused native grant; no final full/build/iOS run is granted.

Root independently read the12:40:25 xcresult summary:203 passed, zero failures/skips,203 total. The owner reports this combined working-source run includes failed article deletion, withheld CloudKit page checkpoint and retained pending sync status. The adapted baseline red and widget fetch/encode/write failure results are owner evidence in the worker's native-fixture record; root has not rerun them.

The historical full-plan result remains791 passes at5013c91. Its independently exported action had zero disk-I/O/vnode-unlink matches. It predates the current consumer/provider/CloudKit fixes. No current-source full Mac plan, normal signed artifact or final generic iOS build is established by that result. The source boundary and focused native resource are now held by the original T30 owner for R21; final heavy runs remain deferred until known review findings stabilize.

## Review frontier

The interrupted R16 runs produced no verdict. Fresh [paired R17 reviews](t30-page-delete-review-r17.md) covered all eight changed-hunk sets at65be895: Standards reported no material Standards finding and separately one Spec P1; Spec reported two P1s (transaction durability and dropped individual record errors). These source-derived findings require correction and behavioral proof. Root's one-line receive-error result correction has parsing proof only; the additional admission-lock assessment remains open. Other review scopes below remain open.

- Page application, token/checkpoint advancement, pending sync status and the new failed SQL delete path, including shared CloudKit callback admission.
- Per-operation send/receive/notification context and controlled queue/selection failure.
- Status command outcomes, partial account success and undo/redo; timeline failure/supersession; widget atomic publication and icon preservation.
- Local refresh overlap and matching callbacks; Feedbin conditional-GET acknowledgement after successful reconciliation; incomplete earlier Feedly/ReaderAPI send/error/rollback coverage.
- Remaining account fixture, storage test and exact-host scripting/build harness coverage, followed by a connected assessment of the complete current API.

Prior verdicts apply only to their stated blobs and seams. Earlier incomplete reviews are not upgraded, and changed/new files are pending. The candidate includes a new deletion correction discovered while testing; it must be reviewed with its queue error propagation and page commit caller, rather than inferred safe from a green count.

After source review clears, the original owner must run final focused checks as needed, exact-host scripting binding before the full Mac plan, action-log diagnostics, a normal isolated acceptance build and strict signature/identity checks, and the appropriate generic iOS build from the same final source. Live-provider, device, production account deletion, personal migration and visible UI remain separate unverified requirements.
