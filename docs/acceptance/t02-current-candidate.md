# T02 current source candidate

Original base: `c9ecfa14e884a7ce8895bb13eec3ea8711cbef90`. Current source HEAD: `4be1246ef430e2166dd06ed2c9e808de4dbd709f`. Local and remote branch refs match and the worktree is clean. The original-base change has 69 paths; the coverage ledger records current blob identities, retaining historical inspections only for identical content.

The coordinator independently reran `python3 -W error::ResourceWarning -m unittest discover -s ManagedEngine/tests -q`: 45 total, 44 passed, one optional reference comparison skipped, zero failures, 26.560 seconds. The earlier coordinator also checked prepared source, manifest and original-base whitespace at this exact HEAD. Owner-reported public controller checks remain separately attributed.

The owner replaced whole-record result/error/identifier allocations with SQLite-backed bounded streaming, including failed auto aggregate resolution. The recorded 16 MiB aggregate first-frame Python allocation peak is 242,449 bytes; it measures traced Python allocations, not process RSS. Deep aggregate nesting remains bounded by the documented parser behavior. Tests do not prove arbitrary stored data or production readiness.

Packaging correction reviews: Spec fully inspected `36fc3ae..eb6a156` with zero actionable P1/P2; Standards fully inspected `51365ee..eb6a156` with zero actionable P1/P2. The latter covers the exact root-entry allowlist and connected assembly/manifest/embed seams. Five public CLI regressions were independently rerun from the extracted pinned correction. Current payload declarations and provenance changed afterward and need fresh delta/seam assessment.

Current-source native signed bundle and CI-path validation remain pending. The r9 installed bundle is stale. The historical 753-test native run applies to `b95cffa`, before later Python-only corrections. Native Settings Ready is unobserved; repeated CUA `cgWindowNotFound` is not evidence of broken UI. Complete native/database/jobs/current packaging and final cross-group reviews remain pending. T02 is open and unintegrated.

Draft PR: https://github.com/lostwildland/NoNews/pull/33 into `feature/nonews-io-parity`, opened to exercise actual CI. It remains a draft while review and current signed-bundle evidence are pending; no issue is auto-closed.

## Current signed bundle and local CI-path validation

The owner completed R20 at `2aa0f6821148049e500912e6131ee9c07fc9ec70`; the artifact uses application/service source `4be1246`, with subsequent changes limited to CI entitlement-path configuration and evidence. The local run uses Xcode 27.1 and the `NetNewsWire-CI` plan, excluding old name-targeted ScriptingTests. Coordinator read `/tmp/nonews-t02-r10-ci-fixed.xcresult`: 747 passed, zero failed/skipped, and independently checked the relocated normal app's deep strict signature and isolated sandbox identity. Owner reports the warning gate passed and ten sandboxed installed-payload harness tests passed. Actual GitHub CI after the push is unknown; a local equivalent is not cloud CI proof.

The pre-T30 test log still contains 2,164 SQLite disk-I/O lines reported by the owner. These remain unresolved fixture diagnostics on this branch. The CI correction passes `CI_SOURCE_ROOT` to Xcode because Swift package targets have a different SRCROOT; its two changed configuration blobs need fresh packaging assessment. The heavyweight resource is released. Visible native Ready, complete independent scope/cross-group review and ticket acceptance remain open.

The coordinator independently reran `bash ManagedEngine/tests/run_native_checks.sh` against the current prepared payload; public controller checks passed.

## Jobs/streaming R21 and CI trigger investigation

Both fresh scoped reviewers completed all eight jobs/streaming files and connected seams at `2aa0f68`. Standards: one P2; Spec: one P2. Both reproduced the same excessive aggregate nesting failure: recursive parsing raises RecursionError, causing a public history read to fail and block older records. Source preservation is intact, but public traversal is incomplete. A bounded parser correction and fresh scoped assessment are required; the scope is not clear.

GitHub reports PR33 mergeable=false/dirty, no workflow runs for head2aa0f68, and Actions enabled. Local merge-tree identifies one add/add conflict in t00-native-baseline.md, caused by independently added T00 evidence plus T02 preparation instructions. [GitHub documents](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) that pull_request workflows do not run while a merge conflict exists. The coordinator reconciles the documentation identically on both branches without importing unreviewed engine code or merging the accepted snapshot implementation into the T02 review range. Real CI remains pending after the correction.

The documentation-only conflict resolution is committed identically on both branches (`ce9fcf0` on the base, `d73d8d2` on T02). Local merge-tree now exits successfully, with no conflict. PR mergeability was still recalculating at observation and Actions had no runs yet; no cloud CI success is claimed. The corrected instructions make engine preparation conditional for engine-enabled branches and avoid running old name-targeted scripting fixtures before T30's exact-host correction.

## Native/IPC Standards scope and source-provenance readback

Fresh native/IPC Standards review at `d73d8d2` inspected all ten group files in full plus connected settings/probe, schema admission and app termination seams. It reports zero actionable P1/P2. A lower-priority deviation remains: programmatic constraints in ProcessingPreferencesViewController.loadView rather than the documented preferred AppKit layout location; no user-visible failure was established. T03 configuration work and T29 UX finish must retain the native layout standard. Native Spec and final connected review remain pending.

Coordinator read-only source hash comparison found all 26 backend files listed in the observed PROVENANCE.md present and matching their recorded SHA-256 in the dirty reference IO checkout. This resolves those listed paths being unavailable to the jobs reviewers; it does not independently prove every extracted schema function or runtime behavior. No personal database/body/credential was read.

After the documentation correction, GitHub reports PR33 clean and mergeable, but no Actions runs or registered workflows. The default-branch workflow file is present, repository Actions policy is enabled, and its token defaults are read-only. Both GET workflow-by-filename and the documented enable endpoint return404. This remote registration/trigger issue remains unexplained and unverified; local747passes must not be reported as GitHubCI. No default-branch merge, permissions escalation or token change was performed.

## Iterative parser candidate and completed native Spec scope

Current T02 candidate `26071ee6cbac80cdcca05e36437e8f9eb695d678` is clean and pushed. The coordinator independently ran the full lightweight suite: 47 total, 46 passed, one optional reference comparison skipped, zero failures, 41.268 seconds. Prepared-source/manifest and original-base whitespace checks pass. The owner replaced recursive aggregate walking with an iterative state walk, spilling nesting state after64KiB, with public1500-level valid/malformed traversal and70000-level spill checks. Fresh jobs correction review is still required. The signedr10 artifact predates this fix.

Fresh native Spec review at d73d8d2 completed all10files plus settings/schema/bundle/environment/apptermination seams with0actionableP1/P2. Native Standards was also complete0. Coordinator blobcomparison confirms all10native files remain unchanged at26071ee; crossgroup and visible UI acceptance remain separate. The jobs classifier causes.py is now grouped with its actual eight-file reviewed jobs scope, leaving27database files and avoiding duplicate coverage accounting.
