# Shared schema admission follow-up

Starting root commit:2e3edb0. T01 issue3 is reopened for a narrow follow-up; previous snapshot acceptance is historical evidence, and personal cutover remains unperformed.

T02 complete database Spec review reproduced two P2s: non-BINARY column comparison can weaken canonical CHECK behavior, and additional rowid/oid/_rowid_ names can hide real row identifiers used for job traversal. The snapshot validator shares this semantic gate, so the coordinator added the same conservative refusals in both copies. Schema41 uses default BINARY comparison; explicit BINARY remains accepted. Unsupported schema and all source data are retained rather than altered. Other unverified custom collations require verified migration.

Public startup regressions failed before the fix for non-BINARY comparison and all three row aliases, then passed. The first snapshot alias fixture used ALTER TABLE, which this installed SQLite refuses; that was an invalid fixture, not a reproduction. The corrected fixture rebuilds the synthetic table with the extra alias. Public snapshot and verify now refuse all cases, publish no destination and leave source bytes unchanged, including when the tampered snapshot hash is recomputed. Explicit BINARY round trips and duplicate-key preservation remain tested.

After releasing only two ignored, inactive, task-owned module caches, the final current suites pass:52snapshot tests in19.197seconds;48engine tests with47passed/oneoptionalcomparison skipped in29.059seconds. Earlier full runs failed during the actual low-space event (snapshot35errors,engine1error); those results are not counted as passes. Focused snapshot/schema checks also pass. No production/private data or native app was used for this follow-up.

Fresh narrow Standards/Spec review is required before T01 is reaccepted. The actual personal migration, remote asset readback, original quiescent-owner/ABA caveats and final native acceptance are unchanged.
