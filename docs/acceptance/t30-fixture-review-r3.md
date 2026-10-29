# T30 fixture repair — round 3 candidate

Original base: `2782c51bae6f68a91baa6b86c88cc0c5fe5a1cb2`  
Candidate HEAD: `dcd563805ab2d9c9fa1d3e7b88d880bac00d1124`  
R2 reviewed HEAD: `ca087f58fb53acd94e6ab21ac0e7dd1168ef5806`

The five-commit, 43-file original-base diff is nonempty and passes whitespace checks. Local and remote candidate HEAD match and the implementation worktree is clean. This is only the fixture-lifetime prerequisite, not full T30 acceptance.

## Correction and evidence

The owner reproduced the admitted-createFeed, queued-OPML, retained-Folder and accepted-sync-reset schedules. Its first ungated sync test was inconclusive; the later test waits for startup reset and holds the actual submitted reset across closure, reproducing the lost selected-row update before correction. Dependent work now keeps tracked admission, dirty OPML is flushed and retained on write failure, retained Folder setters reject without notifications, and accepted resets drain before closure. The new OPML write-failure retry uses only a fixture-owned obstruction.

The owner reports 150 focused tests passed, zero failed/skipped. The coordinator independently read the final full xcresult at `2026.10.28_05-14-20-+0800`: **765 top-level passed, zero failed/skipped**, with 296 parameterized runs. Fresh export/extraction of 1,177 `emittedOutput` fields and 9,646 emitted lines found zero `disk I/O error` and zero `vnode unlinked while in use` matches. One generic main-thread runtime warning remains; this summary does not localize it or call it resolved.

The coordinator also reran the normal acceptance artifact's isolated-identity verifier successfully. It did not rerun the native suite or exercise production deletion/UI/sync. Exact commands and red/green source evidence remain in the worker's `docs/acceptance/t30-native-fixture-lifetime.md`.

## Standards

1 P2, full 43-path fixture scope inspected. Removing Account observers before draining can omit a later accepted folder subscription from OPML: the folder notification no longer marks clean OPML dirty, so flush skips it. The reviewer traced the real createFeed path and cited no-data-loss. This is source-derived, not runtime-reproduced. [Standards review](t3-thread://v1/thread:delegated-task:command%3Amcp%3A5334bca8-6b5e-41fd-84da-2093ead29d99%3Adelegate-task%3Anonews-t30-complete-standards-review-20261028-r3).

## Spec

2 P2, full 43-path fixture scope inspected. Independently found the observer/drain omission through an accepted Feedly move rollback; also found direct Account/Folder container mutation methods accepting retained callers and emitting successful-change events after admission closes. Existing admitted dependent operations must remain permitted, while unrelated membership changes must refuse. Both are source-derived; deterministic regressions are required. [Spec review](t3-thread://v1/thread:delegated-task:command%3Amcp%3A5334bca8-6b5e-41fd-84da-2093ead29d99%3Adelegate-task%3Anonews-t30-complete-spec-review-20261028-r3).

The coordinator re-read both completed reports and connected source, and moved observer removal after successful final OPML flush in the owner worktree. This small correction is uncommitted and unvalidated; the original owner must cover initially clean OPML with an admitted folder mutation/rollback, finish all container admission paths and perform final native validation before committing. No integration or acceptance follows from the prior 765 passes.

## Main-thread warning localization

The coordinator queried the final result's test tree and exact `ScriptingTests/testFeedExists()` details. The runtime warning is attached to that passed test, but no underlying method/source location is provided. Querying the earlier T02 native result `2026.10.28_03-02-21-+0800` finds the identical warning attached to the same test, before this fixture repair. This establishes that the diagnostic predates T30; it does not resolve it or certify UI responsiveness. No AppleScript or app UI was executed for this read-only result inspection.

T30 released the serialized native resource. T02 may use it for the next complete streaming/CI/package validation after its source regressions pass. No current T02 memory correction is claimed.
