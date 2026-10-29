# T30 account lifecycle scope — round 6

Base: `2782c51bae6f68a91baa6b86c88cc0c5fe5a1cb2`; reviewed HEAD: `857cadd5ac96c0f9ea2636707688048bad5f6bc2`. Both independent reviewers confirmed the sixteen ledger blobs, original-base diff, log and whitespace checks. Both read all sixteen changed-hunk sets, but neither certified every connected service callback seam. This is not an account-scope pass or full fixture acceptance.

## Standards

Two source-derived P2 findings, neither runtime-reproduced by the reviewer:

- Public completion callbacks execute inside the provider's still-active background admission. A completion that runs after close begins can submit unrelated new work or mutate retained models successfully.
- An admitted local refresh receives URLSession callbacks outside its TaskLocal context. A completed download can therefore lose its dependent parse/article write when `startBackground` sees closure instead of the original admission.

## Spec

Two source-derived P2 findings, neither runtime-reproduced by the reviewer:

- `triggerRefreshAll` submits an untracked Task before admission; immediate closure can reject that accepted refresh and swallow cancellation.
- The download callback loses admission as above, and network suspension before drain can cancel accepted refresh work while its completion returns normally.

The remaining connected-seam gaps include initialization/migration completion and service-delegate asynchronous/error/rollback paths. Storage, full fixture changes and scripting/harness remain separate review groups.

## Coordinator changes and required continuation

The coordinator changed only two small entry points in the original T30 worktree. Refresh triggering now registers synchronously through the existing background-work entry. `performOperation` captures and restores the caller's original `DatabaseWork` around its completion, preserving legitimate inherited caller context without lending the provider's new admission to unrelated callers. Syntax parsing and whitespace checks pass; these changes are uncommitted and have no runtime regression proof yet.

The original T30 owner must reproduce the callback/trigger schedules, complete the admitted download/parse and network-drain correction with a synthetic real-path fixture, and validate all changes before commit. Keep new unrelated submissions sealed and preserve accepted writes/OPML/callbacks. Do not globally toggle unit-test network bypasses or contact real feeds. Native validation uses the serialized Xcode resource after the T02 timing phase. Prior 769-test evidence is historical until the revised source is tested.
