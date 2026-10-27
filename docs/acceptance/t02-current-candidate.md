# T02 current source candidate

Original base: `c9ecfa14e884a7ce8895bb13eec3ea8711cbef90`. Current source HEAD: `4be1246ef430e2166dd06ed2c9e808de4dbd709f`. Local and remote branch refs match and the worktree is clean. The original-base change has 69 paths; the coverage ledger records current blob identities, retaining historical inspections only for identical content.

The coordinator independently reran `python3 -W error::ResourceWarning -m unittest discover -s ManagedEngine/tests -q`: 45 total, 44 passed, one optional reference comparison skipped, zero failures, 26.560 seconds. The earlier coordinator also checked prepared source, manifest and original-base whitespace at this exact HEAD. Owner-reported public controller checks remain separately attributed.

The owner replaced whole-record result/error/identifier allocations with SQLite-backed bounded streaming, including failed auto aggregate resolution. The recorded 16 MiB aggregate first-frame Python allocation peak is 242,449 bytes; it measures traced Python allocations, not process RSS. Deep aggregate nesting remains bounded by the documented parser behavior. Tests do not prove arbitrary stored data or production readiness.

Packaging correction reviews: Spec fully inspected `36fc3ae..eb6a156` with zero actionable P1/P2; Standards fully inspected `51365ee..eb6a156` with zero actionable P1/P2. The latter covers the exact root-entry allowlist and connected assembly/manifest/embed seams. Five public CLI regressions were independently rerun from the extracted pinned correction. Current payload declarations and provenance changed afterward and need fresh delta/seam assessment.

Current-source native signed bundle and CI-path validation remain pending. The r9 installed bundle is stale. The historical 753-test native run applies to `b95cffa`, before later Python-only corrections. Native Settings Ready is unobserved; repeated CUA `cgWindowNotFound` is not evidence of broken UI. Complete native/database/jobs/current packaging and final cross-group reviews remain pending. T02 is open and unintegrated.

Draft PR: https://github.com/lostwildland/NoNews/pull/33 into `feature/nonews-io-parity`, opened to exercise actual CI. It remains a draft while review and current signed-bundle evidence are pending; no issue is auto-closed.
