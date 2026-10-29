# T02 jobs and controller-fixture review — round 29

Original base: `c9ecfa14e884a7ce8895bb13eec3ea8711cbef90`. Reviewed HEAD: `9c9d4c8b55d545e019e7253d20c767a40584e12c`, with production/test blobs identical to artifact source `91fdf89`. Both reviewers completed all nine assigned files, including the updated native-controller fixture, and connected stdio/authentication/schema/lifetime seams. Their verdicts are scoped, not whole-T02 acceptance.

## Standards

One P2: a synthetic valid 12 MB broad array of small numbers produced no first frame within 10.5 seconds. The existing native request deadline is ten seconds; the resulting native termination is inferred from source, not an app observation. The earlier 500,000-level stack cache does not bound work across the entire supported record size. No separate material Fowler smell was reported.

## Spec

Two P2 findings: a valid synthetic 16 MB aggregate with eight million nesting levels exceeded the native deadline, and an oversized record was reported as an invalid query. The first violates responsive complete-history reading; the second prevents meaningful distinction between capacity and malformed-cursor recovery. The timing probes used temporary synthetic data; neither reviewer reran the full suites or native app.

## Corrections and remaining work

The coordinator reproduced the capacity classification in both normal and aggregate public requests, then added stable `job_record_too_large` error code while retaining invalid-query behavior separately. An initial bootstrap import broke the adapter's fake-backend independence; the final code classifies the domain exception code without adding that import. The final source suite passes 52 total tests: 51 passed and one optional comparison skipped, 28.524 seconds. Rows remain unchanged and subsequent status succeeds. This correction still needs fresh review with the continuing jobs work.

The product contract now requires bounded preparation continuations through the existing cursor interface. Every request must remain within the unchanged native deadline; intermediate progress is not a completed record or empty library. Preserve full 512 MiB encoded capacity, exact contents and source resolution, coherent reads, bounded memory throughout traversal and cleanup on every terminal path. This is ephemeral read work, not a processing workflow or a new persistent job. The original T02 implementation owner must complete and verify it before another jobs-scope review.

The R11 signed artifact is historical for this new correction. Current installed-bundle verification and final connected review remain required afterward. Native Settings Ready is still unobserved; the latest CUA attempt returned `Sky Computer Use native pipe closed before response`, which is not evidence of a product defect. No personal data, models or integrations were used. T01 remains accepted; T02 and full parity remain open.
