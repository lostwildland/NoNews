# T02 current source candidate

Original base: `c9ecfa14e884a7ce8895bb13eec3ea8711cbef90`. Current branch HEAD: `9c9d4c8b55d545e019e7253d20c767a40584e12c`; its only change after artifact source `91fdf89b306c53c65b97df2662348e81db80ce5e` is ticket evidence. The branch is pushed and clean. The 69-path ledger records current blobs; prior scope verdicts carry only for unchanged reviewed content.

The coordinator's latest complete Python run passed 52 total tests: 51 passed, one optional reference comparison skipped, zero failures, 29.408 seconds. Prepared-source/manifest and public Swift controller checks passed. Earlier stale-prepared-source failure remains recorded rather than counted as passing. R27/R28 independent shared-schema/transaction correction reviews now clear both axes. T01 separately passed 53 tests and is reaccepted; this does not clear the remaining T02 scopes.

The owner replaced whole-record result/error/identifier allocations with SQLite-backed streaming. The recorded 16 MiB aggregate first-frame peak is 242,449 traced Python bytes, not process RSS. Its latest cached iterative stack returned first frames for valid and malformed 500,000-level records in 0.762 and 0.775 seconds on this host; the earlier 18.67-second review finding awaits independent post-fix assessment. Public controller checks traverse those records with their existing four-second timeout. These results do not establish production readiness.

Packaging correction reviews: Spec fully inspected `36fc3ae..eb6a156` with zero actionable P1/P2; Standards fully inspected `51365ee..eb6a156` with zero actionable P1/P2. The latter covers the exact root-entry allowlist and connected assembly/manifest/embed seams. Five public CLI regressions were independently rerun from the extracted pinned correction. Current payload declarations and provenance changed afterward and need fresh delta/seam assessment.

The current signed relocated bundle is verified below. Historical 753-test native and 747-test local CI runs retain their original source boundaries; no new full native run is attributed to the Python-only corrections. Native production scopes have earlier complete reviews and unchanged blobs; database corrections are now clear. Jobs, current packaging and final cross-group reviews remain pending. Native Settings Ready is still unobserved; `cgWindowNotFound` is not evidence of a UI defect. T02 remains open and unintegrated.

Draft PR: https://github.com/lostwildland/NoNews/pull/33 into `feature/nonews-io-parity`. Current signed-bundle evidence is recorded; remaining reviews and native UI acceptance are still open, and no issue is auto-closed.

## Current R11 installed-bundle readback

The owner built source `91fdf89` and pushed evidence `9c9d4c8`. The coordinator independently verified the relocated `/tmp/nonews-t02-r11-installed/NetNewsWire.app` isolation identity, deep strict signature and declared embedded source against the checkout. Executable SHA-256 is `69ff3c4f41021f84295365824b925323863008a98f12e33fb89965d79b197f1d`; pre-signing manifest SHA-256 is `3de4de764dc50a57d1a6c0c7f0d8ad85d26389602f93dc1cdb8cbcce103a53aa`. App PID 40629 owns bundled child PID 40647 at readback. The coordinator read the dedicated synthetic sandbox harness result: nine tests, zero failures, EXIT 0, covering the actual bundled schema/settings/transaction/history paths.

Running the stage integrity checker on the signed installed tree does not pass: embedding signs 39 existing Mach-O files under the bundled Python directory, while the retained manifest records their pre-signing bytes. The coordinator confirmed all 39 differences are existing Mach-O files, with no source difference. The installed source verifier and outer deep strict signature pass; the stage manifest is not represented as a post-signing inventory.

CUA inventories the isolated app as running, but exact-path selection returns `cgWindowNotFound`; ID selection is ambiguous among test artifacts. The macOS control surface has no `launch_app` method. Finder Desktop was observable, but a Go to Folder navigation could not produce a readable next state and was cancelled with Escape. No Settings value was changed. Visible Ready remains unverified and is not inferred from process survival or the harness results. Owner-reported private source-copy/cache cleanup remains separate from these coordinator checks.

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

## Database Standards and transaction correction

Database Standards completed27/27pinnedfiles plus reachable startup/settings/read-only preflight seams at26071ee with0actionableP1/P2. It identified a latent retained-helper extraction defect: core.transaction missed the source contextmanager decorator. Ordinary current startup does not invoke its legacy rebuild caller. Coordinator reproduced the TypeError on a private pinned baseline, restored the decorator and added public commit/nested rollback/BaseException rollback checks. Current19bce6b isclean/pushed;48tests47pass1optionalSkip in33.567s,5focusedinitializationchecks, publicSwiftcontroller/preparedsource/manifest pass. Fresh deltaStandards and fullDatabaseSpec are pending; oldscope evidence doesnotclear changed core/testblobs. No currentbundle/nativeUI or wholeT02 acceptance is claimed.

## Database Spec corrections awaiting narrow review

The complete27-file database Spec review at19bce6b found two P2s, reproduced synthetically: a non-BINARY media_type collation can weaken a canonical CHECK, and an extra rowid column can shadow job enumeration. Coordinator added conservative refusal of non-BINARY COLLATE declarations and rowid/_rowid_/oid columns in canonical tables, preserving the input schema/bytes. Explicit BINARY remains accepted. Four public startup regressions failed before these guards and pass afterward. Full current engine suite passes48total,47passed,oneoptionalcomparison skipped in29.059seconds after recovering disk capacity. Matching snapshot guards pass52tests; T01 is temporarily reopened for fresh narrow review.

Jobs Standards R25 completed8/8 and found one P2: individual spill-file seeks on500000nesting levels took18.67seconds, exceeding the native10second request timeout. This still requires a bounded stack-access performance correction. The current test count is not evidence that this known case is fixed.
