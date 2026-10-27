# T02 independent review — round 1

Base: `c9ecfa14e884a7ce8895bb13eec3ea8711cbef90`
Reviewed HEAD: `4a7cc9ef88107c86287507774dd1bfa0b5176d26`
Independent GPT-6.1 Terra high reviewers, read-only; no build, UI or runtime tests by reviewers. The source contains a real source-derived schema/service slice, not the full IO business implementation.

## Standards

2 P2 findings:

1. Failure clears the controller's child ownership before that child exits. Retry can start a second writer, and app termination can skip waiting. Retain ownership through exit, gate retry and wait on shutdown; exercise a child resisting termination.
2. Readiness fetches the default 200 complete job records. A valid large/verbose history exceeds the 64 KiB message cap and makes startup fail indefinitely. Use a bounded real-database readiness read or bounded/paginated response and test populated history.

Worst within Standards: P2. Both corrections remain with the original owner. The readiness finding was independently found on the Spec axis as well; neither axis is merged or reranked.

## Spec

3 findings, worst severity P1:

1. P1: startup schema retirement can drop historical human/observation tables and draft artifact paths from an older database, contrary to retaining unsupported historical forms. Preserve them or refuse before migration.
2. P2: populated-history readiness exceeds the bounded-message channel, as described independently above.
3. P2: startup exceptions become an unexplained unexpected stop and Try Again. Known schema/data/access failures need bounded sanitized codes and meaningful native recovery messages.

The coordinator reproduced and corrected the narrow historical-schema P1 in `97d9948`, with evidence correction `825ec68`. Writable startup accepts new empty data or current schema 41, refuses unsupported populated historical/newer state before journal/schema changes, and closes its connection on refusal. The public regression preserves exact historical rows, artifact path, version and database bytes. A typed safe schema-error code is provided for the pending native error correction.

## Verification and disposition

Before correction, the parent independently ran the seven-test Python suite: six passed and the optional reference-source test skipped. The new historical-start regression first failed because old-schema startup succeeded. After the guard it passed. The first full eight-test run then correctly rejected the stale prepared payload; its source and manifest were refreshed. The final run had eight tests total: seven passed, one optional reference test skipped. The early evidence wording was corrected to retain the failed staging check. Compilation/diff checks passed.

The parent observed the relocated signed app and its bundled child, but `cgWindowNotFound` still blocks native capture even after canonical-path selection and reopening the exact isolated app. Settings Ready and native appearance remain unobserved. The running signed bundle predates the schema correction and must be rebuilt. Intel/universal packaging and full business workflows are not proved.

T02 remains open and unintegrated. Original owner continues lifecycle/readiness/error fixes and canonical-structure startup checks, then rebuilds and returns final evidence for fresh independent review. T03 stays blocked on accepted T02 code.
