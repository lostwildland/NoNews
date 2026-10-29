# T02 independent review — round 8

Original base: `c9ecfa14e884a7ce8895bb13eec3ea8711cbef90`  
Reviewed candidate HEAD: `3e218ade1fae4c9ff5a459979b6a1b3c3f920037`

## Standards

1 actionable P2, and the reviewer explicitly left its remaining first-party/connected-test review incomplete. It reproduced authenticated history projection replacing `Processing stage failed: original detail` with a newer editor-stage error for an orphaned curator job. The stored original was absent from the returned record. Preserve the recorded error and keep any derived stage observation separate. No-data-loss/no-other-bugs priorities apply. [Standards reviewer](t3-thread://v1/thread:delegated-task:command%3Amcp%3A5334bca8-6b5e-41fd-84da-2093ead29d99%3Adelegate-task%3Anonews-t02-orphan-standards-review-20261028-r8).

## Spec

1 actionable P2. The separate reviewer reproduced a canonical `app_settings` trigger passing startup/readiness then deleting retained jobs on a later successful settings PUT. Rollback-only probing cannot establish that arbitrary trigger definitions are safe for subsequent writes. Refuse unverified canonical triggers before writable startup while preserving definitions and records. The reviewer inspected key lifecycle/schema/settings/jobs/package paths but did not inspect every schema owner. [Spec reviewer](t3-thread://v1/thread:delegated-task:command%3Amcp%3A5334bca8-6b5e-41fd-84da-2093ead29d99%3Adelegate-task%3Anonews-t02-orphan-spec-review-20261028-r8).

Neither assessment is a clean acceptance, and the incomplete Standards review must be completed in a fresh review after correction. Both findings used temporary synthetic public stdio probes, not production data or independent full-suite/native evidence.

## Coordinator corrections

The public mixed/all-orphan paging regression now includes recorded wrapper errors and distinct curator/editor stage failures. It first reproduced substitution in both histories. The projection retains the exact stored `error`, including null, classifies that recorded error, and returns a same-named current stage observation separately as `stage_error`. Aggregate details remain in the unchanged `result_json`. No derived mutable stage record overwrites the historical error.

A public startup regression first admitted three canonical trigger variants and a subsequent settings PUT. The managed validator now applies the trigger-refusal rule already present in accepted T01 `_schema41`; source v41 declares no canonical triggers. It returns `schema_migration_required` before mutation, preserving database bytes, original job rows and trigger SQL. The existing native message asks for verified migration. An intermediate `schema_incomplete` response was corrected after a focused status regression. Extra legacy-table triggers remain preserved, and existing settings rollback/timestamp assertions remain. T01 already had the relevant guard and public tests, so no snapshot change/reopening was needed.

Correction HEAD: `897f43c47f83f29efb2b240cb1373ad822c6d70c`, pushed on the original T02 branch. Final full Python suite: 21 total, 20 passed, one optional reference comparison skipped with ResourceWarning as errors. Public Swift-controller checks, prepared source/manifest, compilation and whitespace checks passed. The controller test harness now expects the earlier migration refusal rather than a later write-blocker error; no shipping Swift/native UI source changed.

Current r8 bundle predates these corrections. Actual corrected payload verification, fresh complete two-axis review and native UI evidence remain pending; T30 owns the heavy native resource. No full NNW rerun or new UI observation was made for these Python-only changes. T02 stays open and unintegrated; parent goal and personal migration/sync remain open.
