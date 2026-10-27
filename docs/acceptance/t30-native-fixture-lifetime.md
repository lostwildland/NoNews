# T30 native fixture lifetime: investigation checkpoint

2026-10-28. Starting commit: `2782c51bae6f68a91baa6b86c88cc0c5fe5a1cb2`. This is an investigation checkpoint, not a repair or T30 acceptance. Issue #32 and its feature, migration, sync and UI dependencies remain open.

## Evidence and scope

The existing T00/T02 action logs contain SQLite disk-I/O and open-file unlink diagnostics in synthetic test accounts despite 753 passing tests. The saved T02 action log also reports `DB.sqlite3`, `FeedSettings.db` and `Sync.sqlite3` unlinked during `AccountCredentialsTest.testCreateRetrieveDelete`, so the issue is not limited to a completed Feedbin refresh. The logs do not establish a number of corrupted databases. No personal profile or production data was inspected.

`TestAccountManager.deleteAccount` removes `account.dataFolder` while its argument is still alive. Callers include synchronous `defer` blocks, asynchronous Feedbin refresh tests, and XCTest teardown properties; several hold delegates, feeds or the sync database independently. Some Feedbin tests call cleanup only at the end, so a throw or early return bypasses it. Existing assertions and tests have not been changed.

The following ownership and work make a simple wait for `refreshAll()` or one database queue barrier insufficient:

- `Account` owns the articles database, settings database and delegate. The lazily created `OPMLFile` strongly owns the account, while the account owns it; account initialization loads it. Queued OPML saves can also run later.
- Account initialization dispatches startup cleanup and unread counts to the main queue. Feed settings use asynchronous serial-queue writes. Feedbin initialization schedules a sync-database reset in an unstructured task.
- `ArticlesDatabase` starts a detached authors migration retaining its database queue; it can enqueue another batch after an earlier queue barrier. The queue and settings database own open FMDatabase connections, and the sync actor owns another connection. Closing a connection without preventing later submissions would merely move the failure.
- Production `AccountManager.deleteAccount` also unlinks immediately after marking the account deleted; its lifecycle and notifications need separate consideration if any shared production shutdown is changed. The synthetic logs alone do not demonstrate a production incident.

The repair still needs a deterministic ownership/stop-and-drain design covering those independent work sources and all caller success/error paths, followed by a behavioral regression showing that outstanding work and assertions complete before only the owned directory is removed. No safe close/drain implementation or red/green regression has yet been established. No arbitrary delay or diagnostic suppression has been added.

## Checks and remaining work

- `gh issue view 32 --repo <tracker repo> --json number,title,body,assignees,state,comments`: read the assigned, open issue and its existing blockers.
- Read the saved `/tmp/nonews-t00-r3-action.json` and `/tmp/nonews-t02-r3-action.json` as synthetic evidence. A recursive count of `emittedOutput` lines reported respectively 10,702 and 10,513 disk-I/O matching lines, and 398 and 364 vnode-unlinked matching lines. Action-log entries repeat emitted output; these raw counts are not deduplicated events and are not comparable to the deduplicated counts in `t02-test-diagnostics.md`.
- `swiftc --version`: Apple Swift 6.4; no source compilation was attempted.
- `git diff --check`: passed before this document was added; repeat on the committed change.
- Native targeted red/green tests, full Xcode test action and diagnostic comparison remain pending. Use `buildscripts/acceptance.sh test` and the T00 isolated source-copy machinery when the parent releases the serialized Xcode resource. No xcodebuild or heavyweight Swift package test was run in this checkpoint.
