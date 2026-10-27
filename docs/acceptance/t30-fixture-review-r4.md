# T30 fixture candidate and script-target isolation — round 4

Original base: `2782c51bae6f68a91baa6b86c88cc0c5fe5a1cb2`  
Candidate HEAD: `38f48a749fccf2a7ab35a118a7cbdca9dc2b870c`

Six commits, 44 changed paths; local/remote refs match, worktree clean and original-base whitespace check passes. The candidate fixes R3 observer ordering and retained-container admission, including direct collection setters, single/bulk paths, rollback and released owners. It is not accepted or integrated.

## Native evidence

The coordinator independently read the final `2026.10.28_05-41-38-+0800` xcresult: **766 top-level passed, zero failed/skipped**, with 296 parameterized runs. Export/extraction of 1,178 `emittedOutput` fields and 9,532 emitted lines found zero disk-I/O and zero vnode-unlink matches. The normal acceptance artifact's isolated-identity verifier passed. The owner reports 151 focused passes before a final released-owner assertion; that assertion was included in the full run. One generic main-thread warning remains.

The owner's first observer-only red wrapper changed the wrong suspendNetwork occurrence and was inconclusive; its corrected private-copy baseline reproduced both clean-OPML create-feed and Feedly rollback failures. Do not present the earlier passing schedule as red evidence. Actual commands and test/source-copy checks remain in the worker's ticket evidence.

## Newly inspected script-target boundary

Read-only source inspection found five fixture scripts using `tell application "NetNewsWire"`; `testGetURL.applescript` includes `open location "http://scripting.com/rss"`. AppleScriptXCTestCase loads and executes the compiled fixture without rebinding its target to the current test host. An isolated host identifier alone therefore does not establish the AppleEvent recipient. The T30 diff does not change those scripts/helper, so this is a pre-existing test-harness boundary, not a new T30 regression.

There is no evidence here that the retail profile was changed, and no production profile was inspected to infer it. No AppleScript, app launch or UI action was executed during this source inspection. Prior full counts remain valid execution results but do not prove script-recipient isolation.

Before another full plan containing ScriptingTests, the same fixture owner must bind every application-targeting fixture to the exact current host bundle identifier, refuse unavailable/unbound source rather than execute a name-based fallback, and verify that identifier under the isolated acceptance entry. Keep existing script assertions and do not skip tests or hardcode a retail identifier. Add a behavioral resource/target regression, then validate the isolated full plan and artifact. The installed SDK confirms NSAppleScript has nullable source and initWithSource; unavailable source must be handled explicitly.

Fresh independent Standards/Spec assessment must include this harness change with the existing lifecycle repair before integration. Complete T30, production deletion, iOS, live sync, migration and visible UI acceptance remain open.

## Current R7 candidate for fresh review

HEAD: `209c924aa9f5117f05e5cd33298ff07680cde9ee`, original base unchanged. Seven commits and 53 logical changed paths, including script resource renames. Local/remote refs match, worktree clean, original-base whitespace and isolated-artifact identity checks pass.

The coordinator independently read the final `2026.10.28_06-00-09-+0800` xcresult: **767 top-level passed, zero failed/skipped**, with 296 parameterized runs. The saved action JSON contains 1,179 emittedOutput fields and 10,634 extracted lines, with zero disk-I/O and zero vnode-unlink matches and seven isolated-host marker lines. This extraction has a different line-count boundary from the owner's 9,597 emitted action lines; both retain their stated scope. One generic main-thread warning remains.

The owner binds each application-targeting raw script resource to the exact current host before execution, requires the isolated acceptance bundle identifier under `NNW_ACCEPTANCE_TESTS`, and refuses unbound or unusable source/identity. The URL fixture uses an ignored test URL. The owner reports the non-executing binding test passed before all seven scripting tests. Fresh independent full lifecycle and harness Standards/Spec reviews are required at this exact HEAD. Prior R3 findings were corrected, but no repair acceptance or full T30 acceptance is claimed.

## R4 returned findings — repair remains open

Standards reported two P2 findings: retained Folder.externalID can change OPML/service identity during closure, and retained Folder.unreadCount can change and notify during/after closure. Spec reported two P2 findings: callback operations register only when their queued Task starts, so a pre-close submission can be rejected after close wins; and the same retained Folder setter holes. Both reviews explicitly returned incomplete coverage, so neither clears the slice.

The coordinator inspected the setter callers/OPML consumer and added the small externalID/unreadCount admission guards in the original owner's worktree. These edits are uncommitted and unvalidated pending owner regressions. The owner still needs the substantive callback submission-boundary correction, deterministic pre-task-start tests, during/after-close/released-owner setter checks, full native validation and fresh complete independent review. T02 R20 has released the serialized Xcode resource.

## R8 repair candidate

Original owner pushed `d60871121fdfc00f17c6091d49df71b7bffd3d8b`; originalbase unchanged. Callback operations now register synchronously before theirTask begins, and Folder.externalID/unreadCount are guarded by the existing permit. Coordinator independently read final06:38:42xcresult:768top-level passed, zero failed/skipped, with the existing genericmainthreadwarning; isolated artifact identity and originalbase whitespace pass. The owner reports152focused passes, pre-fix cancellation of seven accepted callbacks plus creation, serial rerun after shared-hook collision, and0SQLite/vnode diagnostic matches. Those log/targeted results remain owner evidence until independently inspected. Fresh full originalbasediff Standards/Spec reviews remain required; every changed hunk and connected seam must be inspected, without requiring unrelated full-file lines of large existing upstream files. This is fixture-slice review, not fullT30acceptance.

Coordinator also independently exported the R8 action log:1,180emittedOutputfields/10,673extractedlines, zero disk-I/O and zero vnode-unlink matches. This extraction boundary differs from the owner's9,640lines and counts repeated/nested emitted output; neither is a deduplicated event count. The negative diagnostic result agrees.

## R5 findings and smaller review scopes

R5Standards inspected18/53paths fully and returned1P2; R5Spec returned1P2 with0/53certifiedcomplete. Both found retained FeedSettings can still write when the account is released without first closing, because its guard only checked the strongly held database. Neither provides a fullfixture pass. Coordinator inspectedall FeedSettings constructors/callers and replaced the shared guard with weak owner availability plus existing account/database admission, passing the owner in bothcacheconstruction paths. This small edit isuncommitted/unvalidated until original-owner regression and native checks, including release-without-close. Future review groups separate lifecycle, storage, fixtures and scripting rather than repeating incomplete53pathassignments; final connectedassessment stillrequired.
