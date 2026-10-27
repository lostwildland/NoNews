## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

A power user previews and commits batch decisions/reprocessing against selected articles or complete filtered results.

## Acceptance criteria

- [ ] Preview pins successful decisions, query scope, policy distribution and phase estimates without enqueueing work.
- [ ] Commit skips reviewed/duplicate/ineligible items and refuses changed routing until re-previewed.
- [ ] Accept AI, process current results and explicit historical reprocessing retain distinct collection semantics.
- [ ] Native selection, progress, undo/cancel and error reporting are functional.

## Blocked by

- https://github.com/lostwildland/NoNews/issues/13
- https://github.com/lostwildland/NoNews/issues/15
- https://github.com/lostwildland/NoNews/issues/16

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
