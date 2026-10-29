# Acceptance module-cache recovery

T30 R9 passed769native tests but its final normal build failed withNo space left on device. Coordinator confirmed about311MiBfree. Initial full snapshot/engine validation also failed during that event; those are not green results.

Read-only inventory found task-owned acceptance-test module caches at about9GiB(T30) and2GiB(T02). After verifying exact regular ignored paths and no xcodebuild/swift-frontend/clang/XCBBuildService process, coordinator removed only those two caches, totaling11,552,300KiB. Source, app artifacts, result bundles, all data containers and credentials were retained. Free capacity returned toabout12GiB. The scoped local cleanup ledger is .scratch/no-news-orchestration/owned-module-cache-cleanup.json.

The first cleanup preflight computed the wrong repository ancestor and refused before any deletion. The corrected ownership check resolved the actual worktree and verified git ignore status. No broader cleanup was attempted.

Each acceptance invocation now stores its Clang module cache in the existing private source copy. Its exit trap removes that cache together with the copy, avoiding persistent caches keyed by ever-changing source-copy paths. Public overlapping-build fixtures assert separate private cache locations and removal; allfive synthetic entry/verifier checks pass inroot,T02andT30. A macOS path-spelling assertion was corrected with resolve(). Actual final-source native validation with the cache setting remains pending. Existing code signatures/sandbox policies were not changed.
