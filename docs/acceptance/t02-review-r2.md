# T02 independent review — round 2

Base: `c9ecfa14e884a7ce8895bb13eec3ea8711cbef90`
Reviewed HEAD: `17fdf64defad0fd44bf607a27de2b3196845bf74`
Independent GPT-6.1 Terra high reviewers, read-only original-base review. Neither reviewer ran builds, tests or UI.

## Standards

1 P2: after launching a child, descriptor duplication can fail before installing its reader/exit waiter. Teardown terminates the child, but nobody transitions out of stopping, so retry and app quit can wait indefinitely. Install exit observation for that path and test it. Worst within Standards: P2. Normal round-one ownership/readiness paths were addressed.

## Spec

3 P2 findings; worst within Spec: P2:

1. Descriptor setup failure leaves lifecycle recovery/quit unbounded, contrary to bounded startup and idempotent stop. This was independently found on Standards as well.
2. Ordinary schema-41 opening still drops empty raw_texts/draft_texts, losing additional columns, indexes and triggers. This violates preservation of imported historical structures and unknown schema objects. Skip retirement during ordinary startup.
3. Readiness is bounded, but job history itself remains inaccessible when its response exceeds the channel limit. The adapter drops the query, so callers cannot ask for smaller pages; one individually large record also needs a usable read path. Provide a bounded, complete read including continuation, preserving actual job semantics and database contents.

## Coordinator corrections and verification

Commit `78304d2` installs an exit waiter before failure teardown when output duplication fails. A DEBUG-initializer fault seam exposes the public failure path: the new controller regression first timed out on the old behavior, then passed after the correction, including completed quit callbacks and repeated start/stop. The existing resistant-child/error/readiness checks also passed through ManagedEngine/tests/run_native_checks.sh.

The same commit removes current-startup empty body-table retirement. A public stdio fixture with extra columns, indexes and triggers first lost those structures; after the fix, two openings preserve the exact sqlite_master inventory. The changed staged schema/provenance and its manifest were refreshed before the full Python run: 11 tests total, 10 passed and 1 optional reference test skipped. Python compilation and diff checks passed. These fixes are not yet in the running installed bundle.

The original implementation owner continues the larger bounded job-history read, caller and public-test changes, followed by final native rebuild/verification. Fresh independent review must compare its final HEAD with the original base. T02 remains open and unintegrated; T03 remains blocked.

## Native evidence limits

The parent independently read the earlier final-source `17fdf64` xcresult (753 passed, zero failures) and observed its relocated app and bundled child. That run predates the coordinator corrections above. CUA inventory recognizes the running isolated bundle without reporting a service error, but full-path selection still fails with cgWindowNotFound and identifier selection is ambiguous among known build/test copies. No screenshot or visible Settings Ready/UX score is claimed. No alternative native capture connector was available in current tool discovery. Intel/universal, iOS, CloudKit and production data remain unverified.
