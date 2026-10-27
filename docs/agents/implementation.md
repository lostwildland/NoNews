# NoNews implementation and review contract

This repository is the user's NoNews fork. The user's explicit authorization to add IO/AI functionality and publish spec/tickets/commits governs this work. Upstream NetNewsWire's contribution approval/no-AI/no-generated-doc policies concern submissions to Ranchero; they do not prohibit this authorized fork. Never submit these changes to upstream without a new request.

Keep NNW's no-data-loss/no-crash/performance priorities and native platform conventions. Current project configuration uses Swift 6.2 and its concurrency settings; the old upstream Swift 5 prose is historical. CLAUDE.md's no-force-unwrapping rule takes precedence over the older optional exception.

One implementation/test owner per ticket: codex/gpt-6.1-terra with reasoningEffort high. Record the starting SHA, read the GitHub ticket and accepted full-parity spec, implement only that ticket, use meaningful public behavioral tests and preserve actual error handling. Do not reduce scope or tests to obtain a green result. Worktree dependencies must come from accepted integration commits, not uncommitted edits or guessed future APIs.

Each ticket's starting commit is the code-review fixed point, not an extra question for the user. The originating ticket/spec is the Spec review source. The root orchestrator runs two independent Standards/Spec assessments; implementers do not silently mark themselves reviewed. Commit and push the ticket branch; acceptance/issue closing happens only after review and required evidence.

Source IO is a separate, dirty live checkout. Read its contracts and current source; do not mutate it or blindly publish its personal constants/credentials. Personal identifiers, paths, collection destinations and taxonomies become user settings. Fixture data must be synthetic. External capabilities and production migration require explicit configured targets and readback; do not confuse fixture tests with real acceptance.

The root owns task_plan.md, findings.md, progress.md and the shared parity matrix. Workers append only their ticket-specific evidence and return structured summaries. Preserve unrelated changes. Do not run simultaneous full Xcode builds on the constrained shared host; separate lightweight Python/Swift fixture checks can run concurrently.
