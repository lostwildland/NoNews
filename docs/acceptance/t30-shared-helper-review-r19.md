# T30 shared SQLite helper correction review R19

Correction base `51d169e477d96bf103c5dd98a673786a50bd363c`; candidate `9ab2069afc779bb8a1cdf6b858c40e45164db017`. The Standards review verified all four scoped blobs, ancestry, the four-path diff (86 additions/22 deletions), log and whitespace. It read all changed hunks and callers. No tests, builds or runtime were run.

Standards found no actionable breach or material Fowler smell. The correction follows current Swift rules, adds no dependency or lock misuse, and captures transaction errors before rollback.

Spec finding: **P1 — `SyncStatusTable.insertStatuses` still leaves a failed transaction open.** It calls `beginTransaction()` without checking and throws after a failed commit without rollback. `SyncDatabase.insertStatuses` returns false, while CloudKit and provider callers can ignore that result and post queued-status notifications. The connection can remain transactional, and pending status reads can become unsafe. Route this path through the same BEGIN/error-capture/rollback helper and add a deferred-COMMIT regression through SyncDatabase: failed insertion rolls back, preserves the pending status and original SQLite error, keeps the connection usable, and a later valid insertion succeeds.

The existing three helper tests cover deferred update commit, failed nested BEGIN and first batch failure, but do not cover this insertStatuses seam. The 217-pass result belongs to the earlier source checkpoint and was not rerun. Full T30, live CloudKit, native/iOS, UI and migration acceptance remain open.
