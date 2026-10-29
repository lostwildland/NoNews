# T30 storage review — round 9

Reviewed range: `2782c51bae6f68a91baa6b86c88cc0c5fe5a1cb2...7accb68382f80c0d4b48c922c8b81899f0364b57`. Both axes verified fourteen storage/queue path blobs and changed-hunk sets. Principal admission, initialization/migration, queued reset, SQLite close/retry and owned fixture-removal paths were examined. Deferred network ownership across all service providers remains outside completed connected coverage; this is not T30 acceptance.

## Standards

One source-derived P2: refused reads/counts and status writes return the same empty collections or zero counts as successful operations. A retained account can therefore appear to have an empty database even though its read was rejected. Rejected queued callbacks also use success-shaped values. The reviewer did not reproduce the issue at runtime.

## Spec

One source-derived P2: `markAsync` and `markAndFetchNewAsync`, including ArticlesTable rejection callbacks, return an empty set for refused writes. Successful status no-ops also return an empty set. The caller cannot tell that a write was never admitted, contrary to the requirement that rejected callbacks report rejection clearly. The reviewer did not reproduce the issue at runtime.

## Interface decision and caller scope

The coordinator inspected the guarded ArticlesDatabase entry points, table callback aliases, Account wrappers, count UI and status callers. This requires a coherent interface correction, not a local replacement constant. Use standard `CancellationError` for admission/queue refusal: throwing value APIs and `Result` callback paths where appropriate. Preserve successful empty/zero results and existing explicit failure channels such as `ArticleChanges.error`, false or documented nil; do not add a global mutable error flag, a notification-only substitute or a framework.

Propagate cancellation through count, fetch/search/ID/date and status callers as required. Background presentation tasks may stop on cancellation while preserving prior state, but must not turn it back into an empty library, fake zero counts, a successful status notification or a destructive synchronization difference. Existing unrelated SQL failure behavior is not automatically redefined by this correction.

The original T30 owner owns this substantial API/caller/test change. Required public regressions distinguish successful empty results from closed/rejected operations, complete rejected callbacks once, preserve admitted writes through drain, and prevent success projections after refusal. No storage API edit has yet been accepted or tested.

## Current checkpoint and validation boundaries

Owner checkpoint `5b2c1a918aaf5f9ed57b15cd92446ee8e70cd9a5` is pushed and clean at handoff. Earlier R7 fixes at source `a92a072b885cf96b02d2b844f9fe5427ad8522cb` have 158 focused passes and 774 full-plan passes. The coordinator independently read the full xcresult: 774 passed, zero failed/skipped. Its 1,187 emitted-output fields contain 9,766 lines and zero disk-I/O or vnode-unlink matches. The current historical normal artifact passes isolation and deep strict signature checks. One generic main-thread runtime warning remains.

The later R8 refresher/parse guard and regressions in `5b2c1a` have only syntax checks; their baseline red run reproduced both reviewed schedules. They still need compilation and green/full/native validation. R9 storage work remains separate.

After a live preflight found no xcodebuild and 8.29 GiB free, T30 confirmed its prior red run had finished. The coordinator explicitly reassigned the serialized native resource to the original T02 owner for current reviewed source `920efef` validation. T30 continues source/regression work without native or timing-intensive execution until a new grant. This resource ordering keeps the T02/T03 feature dependency moving while the fixture correction continues.
