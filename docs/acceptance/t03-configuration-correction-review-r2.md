# T03 configuration correction review R2

Correction base `4075a7d85870d89872e179aa277050ccbef8b850`; head `6fa321f8c9afc966558ba64ff9c595ac173c34aa`. Both reviewers inspected all eight changed paths and connected dispatch, framing/authentication, native pending callbacks, transactions, history, bindings and reference IO contracts. These are source-only correction verdicts, not native UI, Keychain, packaged-runtime, runner or whole-T03 acceptance.

## Standards report

- Standards P2: large previews create durable report snapshots without reclaiming consumed or abandoned copies. Repeated mapping choices can grow storage indefinitely. Bound retention while preserving coherent pagination retries.
- Spec P1: asynchronous preview pages are not associated with the selected service and choices. An older response can mark its display reviewed while Apply submits newer inputs. Use generation/context identity, invalidate review on change and apply the exact reviewed values.
- Spec P2: refreshing after a waiting result drops that state and ignores effective paused claims. Keep waiting/paused/running facts visible across refresh.

No separate material smell was asserted. The report's Spec-labelled findings remain labelled as supplied, rather than being silently counted as Standards violations.

## Spec report

- Spec P1: a pending job's explicit Editor target acquires the selected gateway without proof that it owns the opaque target. Preview hides the missing association and the native report omits the relevant target/service. Preserve proven provenance; otherwise expose the ambiguity and require a reviewed association or leave the job blocked.
- Spec P2: the renderer's 1,000,000-byte expansion heuristic rejects supported materials even when their actual encoded result fits the 1,310,720-byte frame. Preserve material semantics and enforce actual bounded transport without truncation or unbounded allocation.
- Standards P2: the same unbounded durable-preview retention problem.

The reviewers did not reproduce these findings. Both left changes requested. The original owner continues the five distinct correction themes; no new implementation owner or worktree was created.

Follow-up source5154f96 and the fresh paired [R3 assessment](t03-preview-binding-review-r3.md) supersede the correction state above: the original themes have source corrections, but three additional Spec P2s remain. Neither report constitutes whole-T03 acceptance.

## Independent focused check and limits

Root extracted only committed `ManagedEngine` source at the exact head into a temporary test snapshot, removed the optional reference-source environment flags for that subprocess, and ran the three configuration/migration/stdio test modules with system Python, `-B` and ResourceWarning as an error. Seven tests ran in 20.768 seconds: six passed, one optional reference-source comparison skipped. The snapshot was automatically removed after child/test cleanup. This is not runtime preparation or an installed-bundle/native check, and these green tests do not cover the findings above.

Complete oversized envelopes through 8 MiB receive correlated authenticated refusal; larger/malformed envelopes receive an uncorrelated error. Native input is checked against its smaller limit before sending, so that larger case alone is not a demonstrated native-input failure. Earlier unreviewed `legacyMax`-only imports are explicitly refused without changing their rows; recovery is still required if such development records exist. Paper `tag_schema` remains system-owned and unavailable in the configuration-only renderer pending taxonomy/runner integration. None of these boundaries establishes completed runtime or personal-import parity.
