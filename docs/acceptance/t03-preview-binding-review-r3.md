# T03 preview identity and report capacity review R3

Correction base `6fa321f8c9afc966558ba64ff9c595ac173c34aa`; candidate `5154f964e012a19fedf33159e221c3af3f29ebe8`. Both fresh reviewers inspected the ten changed-hunk sets and connected dispatch/authentication, native request state, report generations, Editor receipts, transactions, configuration and source IO contracts. Full-file/test reads were partly truncated. This is a correction review, not whole-T03, native UI or API acceptance.

## Findings

Three distinct Spec P2 findings at the reviewed pin:

- Both reports identify the 16 MiB migration-report cap. Legitimate pending work or accumulated durable evidence can exceed it and become impossible to preview or read back. Controlled refusal preserves data but does not satisfy complete readback. Provide coherent pagination with bounded memory beyond that size, retaining retries, release/eviction and durable apply evidence.
- The Spec report identifies a false post-apply message: the generic snapshot-capacity handler says no mappings were applied, including when Apply already committed and only its subsequent preview failed. Preserve the acknowledgement independently and describe the later error as a readback failure.
- The Spec report identifies ambiguous same-name gateways. Service selection, Editor association and confirmation show names alone although duplicate names are allowed. Show a distinguishing endpoint or stable identifier consistently so the reviewed association is identifiable.

Neither reviewer asserted a separate material Standards violation or Fowler smell. The two-report retention and release address the earlier logical accumulation finding; physical SQLite reclamation remains unmeasured. Source inspection supports frozen review inputs, stale-completion refusal, proven Editor associations, explicit ambiguity/receipt checks and paused/waiting display. These observations do not replace native execution.

## Evidence and continuation

Root previously compiled and executed the exact-head pure Swift MigrationReviewStateChecks: PASS. It constructs only review state; it does not instantiate the engine, compile the preferences controller, use Keychain or prove UI wiring. At that point the preferences typecheck still lacked RSDatabaseObjC; the later check below resolves this source-check limitation only.

Root independently extracted only committed ManagedEngine source at5154f96 into a temporary snapshot and ran the configuration, migration and stdio modules with system Python, bytecode disabled and ResourceWarning treated as an error. Seven tests ran in20.280seconds: six passed, one optional reference comparison skipped. The subprocess excluded IO_TEST_PYTHON and IO_TEST_SOURCE; the temporary snapshot was removed after completion. These public synthetic stdio/SQLite/loopback tests do not cover the three current findings, a declared runtime or native UI.

The original owner resumed the three corrections in the same checkout. T30 retains the serialized native resource; T03 is limited to source, lightweight Python and pure Swift checks until granted. No replacement owner, new worktree, privacy-setting change or provider fallback was introduced. Native/Keychain, declared-runtime, packaged client, runner continuity and UI acceptance remain open. Intermediate legacyMax recovery, system-owned tag_schema and oversized-envelope correlation limits retain their earlier explicit boundaries.

## Later source checkpoint and narrow compilation

Owner checkpoint324f40d commits the acknowledgement/readback message and stable service-ID labels. Those two source corrections still need a fresh paired review. The enabled greater-than16MiB authenticated regression reproduced snapshot_capacity; its test and evidence note remained uncommitted after R6/R7. Neither return completed the connected bounded-report change, and neither established an external blocker. The same original owner now implements the backend preview/storage slice first; native bounded browsing and Apply/evidence streaming remain explicit later work, with the full correction still open.

Coordinator commit `bff22d07649750a1ee214d7df2214b82e956169c` adds one explicit MainActor annotation to the nested gateway-name helper. The existing generated module maps pointed into a removed acceptance-source copy. Using temporary maps to the accepted T02 header tree, existing compiled T02 Debug dependencies and a private temporary module cache, the actual ProcessingEngine and preferences-controller files pass an arm64/macOS15 Swift6 narrow typecheck with warnings treated as errors and no diagnostics. No dependency or Xcode target was rebuilt. Temporary maps/cache/source were removed afterward. Worker evidence is docs/acceptance/t03-preferences-typecheck.md at that commit. This does not prove a linked application, Keychain, declared runtime or visible UI.

Root also compiled and executed the exact bff22d0 engine source with MigrationReviewStateChecks, with warnings treated as errors. The check passed its acknowledgement, waiting/readback-failure, duplicate-name-label and review-generation assertions. It creates no engine or app instance. This verifies the shared pure state API, not the preferences controller's response wiring or visual usability.
