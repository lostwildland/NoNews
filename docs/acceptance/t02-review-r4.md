# T02 independent review — round 4

Base:`c9ecfa14e884a7ce8895bb13eec3ea8711cbef90`
Reviewed HEAD:`8a7de13121717db00fe8fbb992c82d0bcb2eeaf5`
Coordinator correction:`032f258483f52500c8267c5f733babf4b09d3fad`

## Standards

0actionableP1/P2; worst severity none. Independent Terra high reviewer confirmed refs, exact worktree HEAD,19commits and full-original-base scope. Prior lifecycle/atomic-init/framing corrections were present. Some combined output was truncated; the reviewer does not claim every changed line was inspected. No tests/build/UI/production were run by this reviewer.

## Spec

1P2: the current-schema gate checked names without required constraints. A same-column processing_jobs table without primary-key and idempotency uniqueness still passed public stdio readiness. This violates the managed-engine requirement that malformed current data not report Ready because the settings subset works. Required structure must be validated before writable startup, with unknown structures retained. Reviewer reproduced the case in a temporary synthetic database; it did not perform visible UI or production checks.

## Coordinator correction and verification

The canonical comparison now initializes an independent in-memory database with the packaged IO schema owners and compares primary/rowid keys, affinities, default presence/meaning, generated flags, NOT NULL, unique/partial-index predicates, foreign keys and CHECK contracts. The pure signature helper adapts reviewed T01 code; no new external dependency or personal constants were copied. Unproved additional restrictive constraints are conservatively refused; source bytes/unknown BLOB rows remain intact. Existing extra-table/column/index and legacy-trigger positives remain, and an equivalent renamed partial unique index also passes.

Public stdio tests first reproduced9missing/altered invariants being admitted; the generated-column case already refused and remains a preservation check. A second vertical test reproduced4extra restrictive constraints passing a subset-only gate; the complete guard rejects them. Negative cases assert controlled schema_incomplete, no traceback and unchanged bytes. Final full Python suite:19tests,18passed,1optionalreferencecomparison skipped, ResourceWarning as errors. Public Swift controller checks and compilation/diff checks passed. Payload source/manifest was refreshed.

The earlier b95cffa artifact's753macOS test result remains evidence for that unchanged native code, not an execution of this new helper. The original owner next verifies the current packaged/native artifact and installed-bundle refusal behavior. Fresh R5 review remains required. Native visual Ready and the inherited SQLite fixture diagnostics remain unresolved; T30's independent fixture-lifetime repair can proceed from accepted NNW code without claiming whole-ticket acceptance. Full parity and personal cutover remain open.
