# T02 independent review — round 3

Base: `c9ecfa14e884a7ce8895bb13eec3ea8711cbef90`
Reviewed HEAD: `e5e657dd30ccf5d04851476a1193dc8e548b5b16`
Independent GPT-6.1 Terra high reviewers confirmed original-base refs/diff. Each performed a bounded synthetic reproduction; neither ran full suites, native UI/build or production/remote operations. Standards disclosed that its full-diff output was truncated and it did not inspect every changed line; the next review must read bounded per-file diffs rather than treating truncated output as complete coverage.

## Standards

2 P2 findings, worst P2:

1. Fresh schema creation commits multiple owners before stamping version. Interruption leaves partial unversioned tables that subsequent starts correctly refuse as unknown history, permanently preventing ordinary retry. Make fresh initialization atomically publish complete data or use a safely identifiable recoverable protocol, preserving genuinely imported unversioned data. A temporary fault after the first schema owner reproduced it.
2. Each 24,000-byte history frame rebuilds/serializes/hashes the entire record. Traversing a large record has quadratic work and blocks the single service loop. Keep framing and coherent records without rebuilding every frame; add a substantially larger-record complexity check. This is a code-path performance finding, not a measured 100 MB benchmark.

## Spec

2 P2 findings, worst P2:

1. Readiness reads status/settings but does not prove the settings write/read round trip required by the engine contract. Verify actual local settings writability non-destructively and surface failure before Ready.
2. The service emits zero/negative SQLite rowids as continuation cursors but rejects them when read back. A synthetic history with rowids 1/0/-1 reproduced inaccessible records. Accept the full signed range and exercise traversal across zero.

## Coordinator correction and disposition

The coordinator reproduced and corrected the narrow cursor defect. The public IPC regression traverses signed maximum, one, zero, minus one and signed minimum in order and refuses either overflow. After refreshing staged server/manifest, Python passed 13 tests total: 12 passed, one optional reference check skipped. Compilation/diff checks passed. This fix is not yet in the installed bundle; the same owner continues initialization, frame performance and rollback-only readiness proof, then rebuilds for fresh review.

Before correction the parent independently reran the final-source Python and native-controller checks and read the final 753-pass xcresult. SQLite diagnostics were examined separately against the T00 baseline; see t02-test-diagnostics.md. They cannot be dismissed solely because tests passed. Native Settings Ready remains visually unverified; the optional operational window-state question is pending. T02 is open/unintegrated, and T03 remains blocked.

## Original-owner correction and coordinator verification

The owner pushed30d4ba4 with atomic fresh schema creation, rollback-only real-settings readiness and coherent linear per-record spooling. It reported17Python tests(16passed,1optional skip), public controller checks and final-source753macOS tests with zero failures; these are recorded evidence, not visible Settings acceptance.

The coordinator's first independent Python rerun failed the concurrent empty initialization test at PRAGMA journal_mode=WAL(database is locked). The common bootstrap now retries SQLITE_BUSY during journal conversion within the existing30second bound, closes all failed openings and explicitly closes canonical validation connections. The concurrency test coordinates two starts over8emptydatabases, drains/reaps both processes even after failure and retains the unknown-history refusal. Fixture connections now close explicitly. Final focused rerun:18tests,17passed,1optional reference comparison skipped, with ResourceWarning as errors; public native-controller checks passed. Generated payload source/manifest was refreshed after changes and compilation/diff checks passed.

Coordinator correction is pushed at `b95cffa5047bee9f65be99961e4e798e9e36bb63`. The previously launched30d4ba4 app is not final-source evidence for this correction. The original owner must repeat final packaging/build/test and isolated relocated launch before independent R4 review. Native capture of the exact running installed path still returns cgWindowNotFound; no visible Ready or UI appearance claim is made. T02 remains unaccepted, T03 remains blocked, and the full goal remains active.
