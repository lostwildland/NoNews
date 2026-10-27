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

Pending fresh independent assessment of the complete original-base fixture repair, including connected shared database and model callers. R2's findings are not cleared merely by passing tests.

## Spec

Pending separate fresh assessment against issue #32's fixture-repair contract and the scope recorded in the R1/R2 reports. Complete parity dependencies and final issue acceptance remain open.

T30 released the serialized native resource. T02 may use it for the next complete streaming/CI/package validation after its source regressions pass. No current T02 memory correction is claimed.
