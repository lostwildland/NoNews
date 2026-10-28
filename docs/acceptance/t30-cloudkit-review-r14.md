# T30 CloudKit callback ownership review R14

Original base `2782c51bae6f68a91baa6b86c88cc0c5fe5a1cb2`; pin `e46b1b4d03b55204f2c379c26444266168c9776d`. Both reviewers inspected changed hunks in CloudKitAccountDelegate, CloudKitArticlesZoneDelegate and CloudKitSendStatusOperation and checked their three ledger blobs. Connected review is incomplete: account/zone operation middle sections, non-fetch callbacks, migration internals and some evidence reads were truncated or unread. Both axes request changes. There is no CloudKit or full-T30 pass.

## Spec findings

All source-derived, without runtime reproduction:

- P1: shared `CloudKitZone.fetchChangesInZone` starts an actor task from a framework callback without restoring the admitted fetch's DatabaseWork. During close, the account-zone delegate can have its guarded feed/folder mutations refused yet return normally; the zone then advances its change token. Restore the actual fetch's admission and apply/persist the page before advancing the checkpoint. Failure must not acknowledge unapplied records.
- P2: queued send work does not capture its originating admission. MainThreadOperationQueue can start the next operation from a preceding completion's expired or unrelated context. Preserve each accepted operation's own context through completion, including receive and remote-notification paths, without admitting new work after closure.
- P2: status-send selection converts cancellation into an empty successful batch, then completes normally. Return explicit cancellation/error through the operation and enclosing continuation; keep legitimate empty selection successful.

## Standards findings

All source-derived, without runtime reproduction:

- P1: the shared-zone callback loses the matching admitted fetch's context. Pending reads can reject and account-zone mutations can be refused before the token advances. Restore the actual fetch context through page application.
- P1: the operation queue can run a send/receive under a preceding scheduler's expired or unrelated context. Bind each queued operation to its originating work through completion. This overlaps the Spec P2 above; retain each reviewer's severity rather than silently reconciling them.
- P2: the articles-zone delegate substitutes empty pending-status sets for non-cancellation database errors. This can allow remote changes to override pending local state and advance the token. Propagate the error and leave the page retryable.

The original owner has all four distinct correction themes. Tests must use synthetic callback/queue schedules; restoring context must not mint new permission or introduce an RSCore-to-RSDatabase dependency cycle. Full shared-zone, provider and error-path coverage remains pending.

Root read the cited callback, token update, queue submission and selection branches and sent the findings to the original owner for synthetic verification after its coherent consumer batch. This is not execution evidence, authorization for live CloudKit or proof about every provider. Existing passing native counts do not exercise these schedules. No production account, token or cloud record was accessed or changed.
