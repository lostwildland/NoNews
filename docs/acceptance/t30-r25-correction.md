# T30 R25 correction work log

Starting HEAD: `4850b7cf9027c85d4b16f83b3fde352ddd309ef9`. Sole implementation/test owner: GPT-6.1 Sol/high. Existing isolated worktree only. Parent contract/review/coverage documents read; shared trackers remain root-owned.

## Plan and contract

1. Persist pending read/star intent in the same ArticlesDatabase transaction as the local status; transfer to SyncDatabase under the existing status gate and remove the journal only after the transfer commits. Replay before send and remote reconciliation. Preserve original errors. No inverse compensation is needed.
2. Register a bounded fetch lifetime before network work, retaining pending identities plus every local mark during that lifetime through acknowledgement. Reconciliation excludes these identities in both directions while unrelated changes still progress; fetch never holds the status gate. End protection on success/error/cancellation.
3. Run accepted startup resets under the status gate, preserve SQLite errors, and retain close/drain ownership.
4. Add real SQLite and public Account/provider regression sources; run source/lightweight checks only. Native run awaits one coordinated focused grant.

## Scope and risks

Reach: ArticlesDatabase status transaction/schema/journal APIs, Account update/transfer helper, five providers and CloudKit fetch callback lifetime, SyncDatabase gate/reset/fetch protection, storage/account regression sources. New journal is additive and contains only article ID/read/star/flag. Local-only marks and Yep/Nope remain independent. A failed queue transfer keeps the committed local choice and durable intent instead of reverting it. This is the explicit source contract choice for R25, within the authorized no-data-loss correction.

## Progress

- Read R25 first, R24, candidate, coverage manifest, goal/spec/implementation contract, preserved worker evidence, callers and transaction ownership. Worktree clean and remote-matching at handoff.
- Source-only grant prohibits native red/green execution now; regression sources must not be reported as executed. Historical green suites do not validate this source.

## Validation at final source

- `swiftc -frontend -parse` passed for all 20 changed/new Swift source files in this worktree.
- `swift test --package-path Modules/SyncDatabase --scratch-path /tmp/nonews-t30-r25-sync-spm --filter SyncStatusTableTests` passed **13 tests, 0 failures, 0 skips**. It covered fetch protection lifetime and cleanup, acknowledgement overlap, gated reset/send ordering, cancellation/drain, restart recovery, and actual SQLite commit errors. SQLite trigger diagnostics are expected fixture output.
- `swift test --skip-update --package-path Modules/ArticlesDatabase --scratch-path /tmp/nonews-t30-r25-articles-spm --filter StatusOutboxJournalTests` passed **2 tests, 0 failures, 0 skips**. It covered atomic local-status/journal rollback, identical retry, and durable journal recovery across an ArticlesDatabase restart.
- `swift test --package-path Modules/Account --scratch-path /tmp/nonews-t30-r25-account-spm --filter StatusOutboxRecoveryTests` reached a complete Account source and test compile, but the SwiftPM test host terminated before executing the selected tests because existing `RSCore/AppConfig.swift:13` force-unwraps missing `Bundle.main` metadata. No Account test count is claimed from that run. The generated `SecretKey.swift` used for compilation was created from the existing template with all secret environment variables unset, then removed.
- No full Xcode plan/build, iOS build, app launch, device, Keychain, live provider, CloudKit server, or external write was run. No private data or credentials were used.

## Final source limits

The Account/provider regressions are present and typechecked in the focused package compile, but their runtime red/green result remains unavailable because the package test host crashes before test execution. CloudKit fetch protection is covered by a real synthetic zone regression source and the shared SyncDatabase behavior is green. Full provider runtime, live CloudKit, release, migration, and full T30 acceptance remain open.
