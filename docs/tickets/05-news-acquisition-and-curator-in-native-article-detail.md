## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

A news article obtains validated body text and displays a real Curator result in NoNews, with access failures recoverable.

## Acceptance criteria

- [ ] Existing full-text-before-scoring and same-material binding are preserved.
- [ ] Access barriers, runtime absence, timeouts and fallback/manual-required routes remain distinct.
- [ ] Score/title/reason and user prompt output are validated and visible; missing evidence is not a low score.
- [ ] Fixtures prove material identity and no unauthorized browser/session use; actual native rendering is exercised.

## Blocked by

- https://github.com/lostwildland/NoNews/issues/6

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
