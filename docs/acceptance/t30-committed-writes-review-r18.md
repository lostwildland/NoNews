# T30 committed writes and callback recovery review R18

Correction base `65be895bf0bb8534eba3ef9e10973fa03a978185`; tested source `49d80d051e9f199f290191bc4d2b986bee1e9d26`; evidence head `51d169e477d96bf103c5dd98a673786a50bd363c`. The paired reviews covered the 19 changed-hunk sets at the source/evidence pair, but both reported incomplete connected-method coverage. All pins, ancestry, the 671-addition/229-deletion diff and whitespace were verified. No tests or builds were rerun.

## Spec findings

Two source-derived P1s remain:

- Article SQL preparation or iteration failure becomes an empty successful fetch. CloudKit status sending can then construct default updates, delete unusable new rows, send incorrect read/star values and remove selected rows. Preserve the actual query error and retain selected rows until a valid retry.
- A received remote deletion excludes pending starred IDs but deletes other selected sync rows, which can discard an unsent selected read change. Preserve each pending user status until its own successful send acknowledgement; test true no-pending deletion separately.

## Shared SQLite correction

R18 also found a failed sync-row COMMIT can remain unrolled back and make later pending-status reads miss the user's status. Root added `9ab2069afc779bb8a1cdf6b858c40e45164db017`: the shared helper checks BEGIN, captures update/COMMIT errors before rollback, and exposes a result used by SyncStatusTable. Batch insertion stops at the first failure so callers retain the original SQLite error. Added tests cover deferred COMMIT rollback/retry, failed BEGIN inside an existing transaction and first batch failure. These edits are source-only and require fresh compile/review.

Owner evidence at `51d169e` reports 217 focused passes and real deferred-commit/cache/callback/admission regressions. The callback checkpoint is synthetic, not a real CloudKit token; no full-page atomicity, live sync, current full plan, artifact, iOS or UI acceptance follows. Fresh R19 review must include the `9ab2069` four-path helper delta and the two R18 P1 paths. Broader consumers, providers, fixtures and harness remain separate.
