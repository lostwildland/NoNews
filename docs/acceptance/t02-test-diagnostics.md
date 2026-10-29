# Native test SQLite diagnostics

2026-10-28. Read-only inspection of saved test action logs; no test rerun or account/profile access. Console-log extraction was unavailable, so action logs were used. The diagnostic text is not treated as a test pass or production incident.

T00's accepted result `Test-NetNewsWire-2026.10.28_00-28-19-+0800.xcresult` already contains SQLite disk-I/O and “vnode unlinked while in use” diagnostics. T02's result `Test-NetNewsWire-2026.10.28_02-09-35-+0800.xcresult` contains the same diagnostic class. After deduplicating emitted lines, the respective diagnostic counts were 2,358 and 2,347; 96 and 94 lines explicitly named the synthetic NetNewsWireTestAccounts root. Counts include repeated underlying events with different timestamps; they are not counts of corrupted databases or failed tests.

The first T02 group occurs during AccountFeedbinFolderContentsSyncTest.testDownloadSync and names DB.sqlite3, Sync.sqlite3 and FeedSettings.db beneath the temporary test-account root. The T00 baseline includes the same temporary-root unlink class before T02 existed. Modules/Account/Tests had no T02 changes. TestAccountManager.deleteAccount removes that account directory after credential/settings cleanup without an explicit database-lifetime wait in that helper. This is a concrete fixture-lifetime concern; exact shutdown ordering and its effect on assertions still need diagnosis.

Both recorded test plans report 753 passed and zero failed. That does not prove these diagnostics are harmless or that every asynchronous assertion remains representative. The available evidence does not attribute them to the new managed-engine database, and no production data was inspected. T30 must resolve the fixture close/drain/remove ordering and rerun representative/full native checks before final validation claims a clean data-integrity result. Preserve the original functional tests and assertions; do not suppress SQLite diagnostics or exclude the affected tests merely to obtain green output.

Source inspected: Modules/Account/Tests/AccountTests/TestAccountManager.swift and Feedbin/AccountFeedbinFolderContentsSyncTest.swift. No application shutdown or filesystem cleanup was performed in this investigation.

## Candidate lifecycle repair verification

T30 owner delivered9f040dcef27b6665d49bfc18db97a2d745de2ac5 on t3/native-fixture-lifetime, based on2782c51. It implements awaited fixture stop/drain/close and owned-directory removal, preserving functional tests, plus a real busy-close error path and regression coverage. The parent read the final xcresult and confirmed757top-levelpasses,0failures,0skips. Independent extraction from/tmp/nonews-t30-full-action.json found9470emittedlines and0distinct disk-I/O/0vnode-unlink lines. This is stronger than the earlier753green results with diagnostics, but independent code review and integration remain pending.

The new regressions check actual file descriptors/inodes, persisted queued writes, throwing-body cleanup and isolation of another fixture. The owner recorded the baseline red and99targetedpasses. The full result is .build/acceptance-tests/Logs/Test/Test-NetNewsWire-2026.10.28_03-43-09-+0800.xcresult in the T30 worktree. Production AccountManager deletion was not changed or verified by this fixture patch; full T30 integrity/feature/migration/sync/UI acceptance stays open. The existing main-thread warning remains separate.

Independent repair R1 returned Standards 0 and Spec 2 P2 findings: failed Account close cannot retry, and database submission remains open after the close boundary. See [the separate review record](t30-fixture-review-r1.md). The diagnostic-free result does not resolve these lifecycle paths; revised code and fresh validation are required before integration.

## Revised admission candidate

Original T30 owner delivered `ca087f58fb53acd94e6ab21ac0e7dd1168ef5806` after the earlier red checkpoint. The parent independently read final `2026.10.28_04-40-00` xcresult summary: 762 top-level tests passed, zero failed/skipped. A fresh extraction from that result's action log yielded 1,174 output fields and 9,477 emitted lines, with zero disk-I/O and zero vnode-unlink matching lines. The owner's focused final run reports 129 passes. The isolated normal-build identity verifier passed, and the remote head matched.

The revised candidate rejects post-close queue/model/account operations, completes rejections, preserves admitted work and keeps busy-close retry. These source claims still require fresh independent Standards and Spec review from original base `2782c51`; counts do not prove every lifetime path. The summary records one generic main-thread runtime warning without identifying its underlying source here. Production account deletion, iOS/device behavior, migration/sync and full T30 acceptance remain open.
