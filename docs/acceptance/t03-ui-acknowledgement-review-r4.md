# T03 Apply acknowledgement and gateway identity review R4

Pinned correction `5154f964e012a19fedf33159e221c3af3f29ebe8...bff22d07649750a1ee214d7df2214b82e956169c`, containing324f40d andbff22d0. Both fresh reviewers inspected all changed hunks across the five assigned paths: preferences controller, engine/review state, pure Swift check, native configuration evidence and narrow typecheck evidence. They traced preview/page failures, Apply, invalidation, service selection, Editor association and main-actor callbacks. This is not whole-T03 or API acceptance.

## Standards report

No actionable documented Standards violation and no material Fowler smell. The report separately identifies a Spec P2: the historical waiting acknowledgement can still claim claims remain paused when a newer report says claims are active. Show historical acknowledgement separately from the refreshed effective state. The reviewer did not reproduce this schedule.

## Spec report

Two source-derived P2 findings, without execution:

- An Apply callback records and publishes its result without checking whether the originating input or selected service has changed. A response for A can appear on B's newer report; historical waiting can also contradict current active claims. Bind acknowledgement to its immutable originating input and prevent stale publication.
- Pressing Preview clears the confirmed Apply acknowledgement. Retrying a failed post-apply readback therefore loses the independent confirmation, and another failure produces only a generic error. Preserve the confirmed result across readback retries.

Both reports support stable-ID labels for identical service names and the explicit MainActor annotation at source level. Their typecheck and pure-state evidence was supplied by the coordinator, not independently rerun. Live issue5/comments were not fetched under the reviewers' interpretation of the network restriction; they read the pinned local ticket/spec and previous reports. Native app/UI/Keychain and T11 checks remain open.

## Correction boundary

The coordinator temporarily owns only ProcessingEngine.swift, ProcessingPreferencesViewController.swift and MigrationReviewStateChecks.swift for these small findings. The original implementation owner retains backend report storage work, with a source-boundary steer delivered before edits. Existing public state checks supply the authorized regression seam; no further requirements interview, app launch or inference is needed. New source and check outcomes are recorded after execution.

## Implemented correction awaiting re-check

Coordinator commit `b279f1d85d926d8946127518f697016bf44a312f` is pushed and remote-verified on the ticket branch. Apply has a separate request generation and immutable input; preview retries preserve its tagged acknowledgement, stale Apply responses cannot replace a newer Apply, and the controller publishes a result only for the current matching input. Historical waiting is labelled as the earlier Apply, while the report gives current effective state. Changing or creating a service clears old routing choices and report controls.

The pre-fix public state executable compiled and exited1 with the expected historical-pause failure. The fixed check executes successfully for cross-service response, superseded Apply, repeated readback retry, historical waiting/current active state and unknown response. The final actual pane/engine sources pass a narrow Swift6 arm64/macOS15 typecheck with warnings treated as errors and no diagnostics using matching accepted T02 compiled dependencies and temporary Clang maps. This is not linked-app/UI/Keychain execution. Fresh paired correction review remains required.
