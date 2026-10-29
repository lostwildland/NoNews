# T01 shared-schema follow-up acceptance

Accepted current snapshot source: `d9c18afa8fc14de92d67508db675c30cf3d8da5c`, already on the integration branch. The coordinator confirmed no later difference in the snapshot source/tests and confirmed the pushed integration ref before reacceptance. The original full implementation and its independent restore evidence remain in [round 7](t01-review-r7.md).

The shared-schema follow-up began at `2e3edb06c79e73664f1e62958346a72134fdc820`. It refuses non-BINARY comparison rules and columns that shadow SQLite row identifiers, without altering the input. R26 found over-refusal of valid single-quoted BINARY names; R27 found the same compatible annotation inside a canonical CHECK. Both corrections retain case-sensitive quoted literals and refuse non-BINARY comparison rules. Unknown harmless columns and their data survive the public round trip.

## Standards

R27 completed all three root files and connected schema/test seams with zero actionable P1/P2 findings. Fresh R28 reviewed `eacdcd91fec1249debda34c0332b1adf28ff3e70...d9c18afa8fc14de92d67508db675c30cf3d8da5c`, including all three changed files and connected normalization/admission seams: zero actionable P1/P2 findings and no material Fowler smell. The reviewers did not rerun the coordinator's full suite.

## Spec

R27's equivalent-CHECK finding was reproduced before correction. Independent R28 covered the same three-file delta and CHECK/default/partial-predicate/collation-name callers with zero actionable P1/P2 findings. It confirmed normalization of six BINARY spellings without weakening quoted-literal comparison or non-BINARY refusal. Both axes verified pinned objects, nonempty logs/diffs and whitespace checks.

## Verification and disposition

The final integration-root public suite passed 53 tests in 19.987 seconds with ResourceWarning treated as an error. The added checks exercise all six BINARY spellings on a column and canonical CHECK, preserved rows/extra columns through snapshot/verify/restore, changed string-literal refusal and quoted/unquoted NOCASE refusal without publication or source mutation. Compilation and whitespace checks passed.

T01 is reaccepted for its current-schema developer snapshot/verify/restore interface. This closes only the shared-schema follow-up. Quiescent source writers are still required; the observations cannot prove global atomicity or detect ABA changes. Personal data migration, remote readback, recovery consumers, native import/rollback and resumed integrations remain T21/T27/T30 work. No personal database or credentials were opened; the parent goal remains active.
