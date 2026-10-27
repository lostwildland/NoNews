# T02 independent review — round 7

Original base: `c9ecfa14e884a7ce8895bb13eec3ea8711cbef90`  
Reviewed candidate HEAD: `316e9ba4f755cbac85f6958d5991899f419b44c0`

## Standards

1 actionable P2. The independent reviewer completed the first-party production/test scope and reproduced an authenticated job-history failure: the record query used an inner join to items, while its next cursor selected every processing job. A missing referenced item between two valid jobs made the next cursor fail; an all-orphan history appeared empty. Startup admitted the synthetic current-schema database. This conflicts with the repository's no-data-loss/no-other-bugs priorities. [Standards review](t3-thread://v1/thread:delegated-task:command%3Amcp%3A5334bca8-6b5e-41fd-84da-2093ead29d99%3Adelegate-task%3Anonews-t02-complete-standards-review-20261028-r7).

## Spec

0 actionable P1/P2 findings, worst none. The separate reviewer completed the T02 scope against issue 4 and the managed-engine contract, including startup/schema, actual settings probe, native lifecycle, private IPC, job framing, packaging and corresponding tests. It did not review T01 or rerun owner suites. [Spec review](t3-thread://v1/thread:delegated-task:command%3Amcp%3A5334bca8-6b5e-41fd-84da-2093ead29d99%3Adelegate-task%3Anonews-t02-complete-spec-review-20261028-r7).

## Coordinator correction and pending gates

The coordinator added a public authenticated-stdio regression covering mixed valid/orphan and all-orphan histories, large retained result frames, preserved identifiers/errors, no fabricated title, unavailable/retry state and unchanged persisted job rows. Both scenarios failed before the fix: invalid continuation and hidden empty history respectively.

The record query now enumerates every job with a left join, retains the missing reference and result, and explicitly returns `itemUnavailable` with a retry-blocked explanation. It does not delete, repair or run the orphan. Other records and older history remain accessible. Three focused paging tests passed; after prepared-source/manifest refresh the full Python suite passed 20 total, 19 passed and one optional reference comparison skipped under ResourceWarning-as-error. Public Swift-controller checks and Python compilation/whitespace checks passed. These are current-source checks, not new bundle or native-UI evidence.

The original T02 owner must refresh the real bundled payload and verify this history behavior through the relocated signed service before fresh independent recheck. No repeated full NNW suite is required for this Python-only change. Native visible Settings Ready, release signing, Intel/universal, iOS, production migration and full parity remain unverified. T02 stays open and unintegrated; T30's currently failing admission regression is a separate original-owner worktree and is not integrated.
