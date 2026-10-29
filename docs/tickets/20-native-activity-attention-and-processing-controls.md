## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

A user views real jobs, failures and history and can change processing capacity or retry/cancel at the correct scope.

## Acceptance criteria

- [ ] Preserve Jobs/Needs attention/History, failure grouping, same-cause retry, dismiss and resolved-history semantics.
- [ ] Worker limits/current scope are configurable; cancel queued does not falsely claim to kill running work.
- [ ] Health/worker presence is not reported as end-to-end integration success; 400-row windows are not global totals.
- [ ] Service errors do not interrupt ordinary NNW reading or leak request bodies/secrets.

## Blocked by

- https://github.com/lostwildland/NoNews/issues/4
- https://github.com/lostwildland/NoNews/issues/13

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
