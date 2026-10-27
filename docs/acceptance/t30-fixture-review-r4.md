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
