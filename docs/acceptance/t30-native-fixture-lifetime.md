# T30 native fixture lifetime: investigation checkpoint

2026-10-28. Starting commit: `2782c51bae6f68a91baa6b86c88cc0c5fe5a1cb2`. The following initial investigation preceded the implementation described below. Issue #32 and its feature, migration, sync and UI dependencies remain open.

## Evidence and scope

The existing T00/T02 action logs contain SQLite disk-I/O and open-file unlink diagnostics in synthetic test accounts despite 753 passing tests. The saved T02 action log also reports `DB.sqlite3`, `FeedSettings.db` and `Sync.sqlite3` unlinked during `AccountCredentialsTest.testCreateRetrieveDelete`, so the issue is not limited to a completed Feedbin refresh. The logs do not establish a number of corrupted databases. No personal profile or production data was inspected.

`TestAccountManager.deleteAccount` removes `account.dataFolder` while its argument is still alive. Callers include synchronous `defer` blocks, asynchronous Feedbin refresh tests, and XCTest teardown properties; several hold delegates, feeds or the sync database independently. Some Feedbin tests call cleanup only at the end, so a throw or early return bypasses it. Existing assertions and tests have not been changed.

The following ownership and work make a simple wait for `refreshAll()` or one database queue barrier insufficient:

- `Account` owns the articles database, settings database and delegate. The lazily created `OPMLFile` strongly owns the account, while the account owns it; account initialization loads it. Queued OPML saves can also run later.
- Account initialization dispatches startup cleanup and unread counts to the main queue. Feed settings use asynchronous serial-queue writes. Feedbin initialization schedules a sync-database reset in an unstructured task.
- `ArticlesDatabase` starts a detached authors migration retaining its database queue; it can enqueue another batch after an earlier queue barrier. The queue and settings database own open FMDatabase connections, and the sync actor owns another connection. Closing a connection without preventing later submissions would merely move the failure.
- Production `AccountManager.deleteAccount` also unlinks immediately after marking the account deleted; its lifecycle and notifications need separate consideration if any shared production shutdown is changed. The synthetic logs alone do not demonstrate a production incident.

The initial investigation identified the need for deterministic ownership and stop-and-drain handling across those work sources and all caller success/error paths. The implementation and regression below address the fixture path. No arbitrary delay or diagnostic suppression has been added.

## Checks and remaining work

- `gh issue view 32 --repo <tracker repo> --json number,title,body,assignees,state,comments`: read the assigned, open issue and its existing blockers.
- Read the saved `/tmp/nonews-t00-r3-action.json` and `/tmp/nonews-t02-r3-action.json` as synthetic evidence. A recursive count of `emittedOutput` lines reported respectively 10,702 and 10,513 disk-I/O matching lines, and 398 and 364 vnode-unlinked matching lines. Action-log entries repeat emitted output; these raw counts are not deduplicated events and are not comparable to the deduplicated counts in `t02-test-diagnostics.md`.
- `swiftc --version`: Apple Swift 6.4; no source compilation was attempted.
- `git diff --check`: passed before this document was added; repeat on the committed change.
- At the investigation checkpoint, native targeted red/green tests, the full Xcode test action and diagnostic comparison were pending. Subsequent results are recorded below.

## Implementation and focused validation

The account fixture now records its own UUID directories and uses an awaited cleanup on success, thrown error and XCTest teardown. Shutdown marks the account closing, stops network activity and observers, waits for tracked account operations and background work, waits for the delegates' startup sync reset and the authors migration, stops recursive article indexing, and closes the sync, article and feed-settings connections through their owners before removal. The OPML file now holds a weak account reference; a queued save sees the deleted state. Recursive work from local parsing and CloudKit initialization is tracked as account background work. The fixture-only shutdown entry does not change `AccountManager.deleteAccount` notification or logout behavior; production deletion is not claimed repaired here.

FMDatabase previously returned success and discarded its SQLite handle even if `sqlite3_close` failed. It now reports failure and retains the handle for a retry. The real SQLite-backup regression verifies a busy close fails and a later close succeeds. Existing Feedbin folder, read and starred-status assertions remain, with awaited fixture cleanup added around them. The new fixture regression checks database file descriptors and inodes, completed synthetic refresh and starred status, queued feed-setting persistence after close, cleanup on a thrown body, and preservation of a separate account directory and rejection by a non-owning manager.

For a red baseline, `buildscripts/acceptance.sh test` was run with a temporary xcodebuild wrapper that restored modified Swift files inside the generated acceptance source copy to `2782c51bae6f68a91baa6b86c88cc0c5fe5a1cb2` and added a baseline-compatible inode regression. `-only-testing:AccountTests/AccountFixtureLifetimeTests` failed with three assertions: all three original database inodes were still open after the old deletion. `/tmp/nonews-t30-red.log` also records vnode-unlink diagnostics for `DB.sqlite3`, `Sync.sqlite3` and `FeedSettings.db`, followed by disk-I/O diagnostics. Xcode subsequently pruned that red result bundle; the log remains the evidence. This run preceded termination of the separate T02 acceptance app.

An initial targeted run also preceded termination of that app. The first busy-close test incorrectly used the backup destination and crashed; it was corrected to use the busy source and to finish the backup before closing either handle. That failed attempt is recorded in `/tmp/nonews-t30-targeted-r3.log` and is not green evidence.

Before the clean rerun, process inspection confirmed PID 91127 ran `/private/tmp/nonews-t02-r6-installed/NetNewsWire.app/Contents/MacOS/NetNewsWire`, and PID 91139 was its child running that bundle's engine. `NSRunningApplication.terminate()` was requested for the exact matching app bundle and returned true; subsequent `ps -p 91127,91139` showed neither process. No other app was stopped.

`PATH=/tmp/nonews-t30-tools:$PATH buildscripts/acceptance.sh test`, using a wrapper adding `-only-testing:AccountTests -only-testing:RSDatabaseTests/DatabaseCloseTests`, passed 99 tests with zero failures or skips. Result: `.build/acceptance-tests/Logs/Test/Test-NetNewsWire-2026.10.28_03-42-06-+0800.xcresult`; log: `/tmp/nonews-t30-account-r6.log`. `xcrun xcresulttool get log --type action` on that result reported zero literal or distinct disk-I/O and vnode-unlink lines. The test intentionally emits SQLite error code 5 when exercising the busy close; this is asserted behavior, not suppressed output.

## Full native plan

After the isolated T02 app was stopped, `buildscripts/acceptance.sh test` completed successfully using its private source copy. The result bundle is `.build/acceptance-tests/Logs/Test/Test-NetNewsWire-2026.10.28_03-43-09-+0800.xcresult`; the console is `/tmp/nonews-t30-full-final.log`, and `xcrun xcresulttool get log --type action --path <result>` produced `/tmp/nonews-t30-full-action.json`. `xcrun xcresulttool get test-results summary --path <result> --compact` reports 757 top-level tests passed, zero failed or skipped, with 296 parameterized runs; its device-level count is 1,004 passed. One existing main-thread runtime warning is recorded; it is not a SQLite diagnostic.

Recursively extracting `emittedOutput` lines from the action logs and comparing exact distinct lines gives: T00, 2,262 disk-I/O lines and 96 vnode-unlink lines (all 96 name the test-account root); T02, 2,253 disk-I/O lines and 96 vnode-unlink lines (94 name that root); this T30 full run, zero of either class. Raw repeated action-log occurrences are respectively 10,702/398, 10,513/364, and 0/0. Disk-I/O lines do not themselves name paths. These are diagnostic-line counts, not database-corruption counts. This is fixture test evidence, not a claim about production account deletion, live sync, migration, other devices or final T30 acceptance.
