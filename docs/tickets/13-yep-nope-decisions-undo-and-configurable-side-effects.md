## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

A reader can decide without AI prerequisites, undo, and safely stop or continue processing according to explicit settings.

The [native decision contract](../specs/native-decisions.md) specifies acknowledgment versus commitment, source undo deadlines, later Clear Decision, scope-safe navigation, NNW gesture coexistence and configurable integration side effects. Preserve the source semantics and the user's Yep-stays exception; do not map legacy IO read aliases onto NNW read status.

## Acceptance criteria

- [ ] Yep stays; Nope advances only within current results and handles end-of-list; Star/read are independent.
- [ ] Preserve command intent/audit and duplicate observations; do not train recommendations.
- [ ] Nope invalidates pending/late work authorization; cleanup preference is surfaced without weakening protected-reference checks.
- [ ] Undo/restoration has real public behavior and native keyboard/buttons/gestures with accessible labels.
- [ ] Integration linkage is configurable; a decision alone is never reported as external success.
- [ ] Native Undo respects the pending-command deadline and worker races; Clear Decision reopens the human judgment without changing NNW read/Star. Unknown acknowledgments reconcile the same operation identity.
- [ ] Read/Star swipes remain available; decision swipes are an explicit device preference with equivalent keyboard/menu/button actions. Late responses and undo do not steal a newer selection.

## Blocked by

- https://github.com/lostwildland/NoNews/issues/6

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
