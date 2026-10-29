# T30 page and deletion correction review R17

Correction base `e46b1b4d03b55204f2c379c26444266168c9776d`; reviewed head `65be895bf0bb8534eba3ef9e10973fa03a978185`. Fresh paired reviews replaced the interrupted R16 runs. Both verified all eight pinned blobs, the six-commit log, nonempty 79-addition/37-deletion diff and whitespace checks. Each read all eight changed-hunk sets and the named page/delete/queue test methods. Neither ran tests or live CloudKit.

## Standards axis

No material documented Standards breach or Fowler smell was found in the bounded correction. The Standards reviewer separately reported one **Spec P1**: article deletion reports its SQL result before the enclosing transaction commits, while DatabaseQueue ignores commit failure. This is not a Standards pass for the entire ticket.

## Spec axis

Two **P1** findings, both source-derived and not runtime-reproduced by the reviewer:

- `ArticlesTable.delete` posts success from inside the transaction body; `DatabaseQueue._runInDatabase` ignores the later commit result. A failed commit can therefore be followed by pending sync-row removal and page acknowledgement despite an uncommitted article deletion. Complete the transaction successfully before reporting success; preserve retryable state on begin, statement or commit failure.
- `CloudKitZone.fetchChangesInZone` ignores an individual record error through `try? result.get()`. A successful overall fetch can then apply an incomplete page and advance its token. Retain per-record errors and fail the page, preserving callback ordering and retryable token state.

The reviewed correction restores captured work for page application and queued send, propagates pending reads and DELETE statement failures, and distinguishes empty selection from errors. Its tests do not establish commit failure, the actual framework callback sequence, every statement-step error or live retry. The 203 focused passes apply to combined precommit source; the historical 791-pass plan applies to `5013c91`. Neither validates the pending corrections.

## Coordinator follow-up outside this eight-path verdict

Root found that `CloudKitReceiveStatusOperation.failure` was declared and checked by its caller but never assigned in the catch path. Commit `926bbe30e9dec29d29c5ad3341022d1829a533be` adds the missing assignment; Swift frontend parsing and whitespace checks passed. A queued failing-refresh regression and native validation remain required.

Root also found synchronous SQL/queue waits inside FeedSettingsDatabase's admission lock; see [admission assessment](t30-admission-assessment.md). This was not covered or cleared by the R17 verdict. The original T30 owner must complete the connected repairs and focused behavioral checks before fresh independent re-checks. Full native/build/iOS, live sync, production deletion, migration and UI acceptance remain open.
