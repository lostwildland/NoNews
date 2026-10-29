# T02 packaging Standards review — round 10

Original base: `c9ecfa14e884a7ce8895bb13eec3ea8711cbef90`  
Reviewed candidate: `d21a38dd8e9822746c5ccc6b85a74e71a03d56d2`

## Standards

Packaging scope complete, with 1 actionable P2. The independent reviewer inspected all 19 packaging-group paths and verified their blob identities against the coverage ledger. It also traced project phase wiring, the macOS CI workflow, source generation, preparation/manifests, bundle discovery and the stdio seam. Other scopes remain pending. [Review](t3-thread://v1/thread:delegated-task:command%3Amcp%3A5334bca8-6b5e-41fd-84da-2093ead29d99%3Adelegate-task%3Anonews-t02-packaging-standards-review-20261028-r10).

The unconditional engine embed phase requires a prepared ignored payload and a signing identity, while the existing fresh-checkout macOS CI job supplies neither. That stops the existing test plan before tests execute.

## Coordinator correction

Small correction `36fc3ae6b057a5fe07e1b831e88c90b62958cded` is pushed on the original implementation branch. macOS CI now prepares the pinned payload before its unchanged test plan and uses a clearly named ad-hoc signing configuration with an isolated `org.nonews.ci` identity and the existing acceptance sandbox entitlements. iOS's unsigned configuration remains unchanged. The embed script's integrity, architecture and signing-identity guards remain intact.

Static order/configuration checks and whitespace checking passed. No Xcode test/build, GitHub CI run or bundled runtime check has validated this correction yet; T30 held the native resource at edit time. The original T02 owner retains its uncommitted partial streaming implementation and must finish it, then validate the CI path after the now-released native resource is assigned. The source-only correction is not acceptance.

## Spec and remaining coverage

Independent packaging Spec inspection is complete at `36fc3ae6b057a5fe07e1b831e88c90b62958cded`, with 2 P2 findings across 22 paths (the previous 19 plus three CI paths, including the deleted unsigned configuration). It traced preparation, source copying, manifests/signing, project phases, sandbox and CI. It source-reviewed the CI correction while keeping actual execution unproven. [Spec review](t3-thread://v1/thread:delegated-task:command%3Amcp%3A5334bca8-6b5e-41fd-84da-2093ead29d99%3Adelegate-task%3Anonews-t02-packaging-spec-review-20261028-r10).

First, whole-directory backend copying could include an untracked private `.env` or Python file, and the source verifier ignored non-Python extras. Second, the documented fresh-checkout acceptance sequence omitted the now-required explicit runtime preparation. Both were source-derived findings; no private files or native runtime were inspected by the reviewer.

## Source-boundary correction

Coordinator correction `51365ee` is committed/pushed on the original T02 branch. A shared explicit declaration permits only the 27 currently committed public backend modules and four required root resources. Assembly prechecks declared regular files and copies only those; source verification rejects any extra backend entry and symlinked source/staging entries, even if an attacker regenerated the ordinary integrity manifest. The fresh-checkout sequence now prepares its ignored runtime before build. The newly authored but incomplete/uncommitted `job_stream.py` remains outside this committed declaration; the owner must add it with its actual source change, not publish a declaration requiring a missing file.

Four synthetic public-CLI tests failed against the former implementation and passed after correction: exclusion of a fake private `.env`/Python file; refusal of extras after manifest rewrite; source symlink refusal before manifest publication; and staged backend-directory symlink refusal. Tests use generated sentinel files and no private configuration. Python compilation, explicit declaration-to-committed-tree equality and whitespace checks pass. No Xcode, actual runtime preparation or final signed bundle was exercised for this correction while T30 owns that resource.

The coordinator has handed the declaration back to the original owner for deliberate future-module additions and final source/manifest refresh. These changed/new blobs still need fresh independent assessment; neither the old 19-file Standards inspection nor 22-file Spec inspection clears the correction automatically. All native/database/jobs scopes and the final connected assessment remain required. No whole-T02 clearance, integration or visible UI acceptance is claimed.

## Standards correction review — round 11

Complete inspection of the eight-path correction range `d21a38d...51365ee` found 1 P2: exact backend membership was checked, but root extras could still be included after regenerating an ordinary manifest. No actionable smell was reported. This is a source-derived finding; the reviewer did not run tests. [Standards review](t3-thread://v1/thread:delegated-task:command%3Amcp%3A5334bca8-6b5e-41fd-84da-2093ead29d99%3Adelegate-task%3Anonews-t02-packaging-correction-standards-review-20261028-r11).

Coordinator correction `eb6a156` checks the complete payload root against the four declared resources, `backend`, `python` and the manifest. A new synthetic CLI regression reproduced acceptance of both an extra root `.env` and JSON file after manifest rewrite, then passed after correction. The existing four regressions still pass: **5 total** under ResourceWarning as errors. The verifier also accepts the current prepared root, whose seven entry names were inspected without reading private data. Compilation and whitespace checks passed. No Xcode, current signed-bundle or CI run was performed; fresh correction assessment remains required.

## Streaming checkpoint, separate from packaging acceptance

The original owner's R18 continuation now streams non-aggregate error/result/text fields and retains cause classification across chunks. Its 16 MiB result/error/identifier cases report less than 243 KiB of traced Python allocations; this is not a claim about total process/SQLite memory. The owner's recorded 39-test run before the new root-entry regression had 37 passed, one failed aggregate allocation check and one optional reference skip. It reports passing controller/source/manifest checks after refresh. All streaming changes remain uncommitted; the enabled failed-`auto` case still used 33,567,195 traced bytes. Complete aggregate semantics, final full checks, native/CI/bundle validation and independent review remain outstanding.

## Source-boundary Spec correction assessment

The fresh independent Spec assessment of `36fc3ae...eb6a156` completed all five changed paths and connected preparation, manifest, embed and acceptance seams with **0 actionable P1/P2 findings**. It verified the declaration against the pinned 27-file committed backend, not the live streaming worktree. This clears only the source-boundary correction on the Spec axis. [Spec review](t3-thread://v1/thread:delegated-task:command%3Amcp%3A5334bca8-6b5e-41fd-84da-2093ead29d99%3Adelegate-task%3Anonews-t02-source-boundary-spec-review-20261028-r11).

The coordinator separately extracted the five required scripts/tests from commit `eb6a156` into a temporary directory and reran the synthetic public-CLI suite there: **5 passed**, ResourceWarning as errors. This verifies the committed correction independently of the owner's uncommitted source/declaration. No backend service, native app, private data or network was used. Standards still needs a fresh assessment of the final two-path root-entry correction; current CI/bundle validation and all other scope gates remain pending.
