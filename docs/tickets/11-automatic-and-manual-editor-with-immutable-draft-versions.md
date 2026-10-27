## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

A reader receives an Editor draft via configured automation or explicit action and can rerun, inspect and compare versions.

## Acceptance criteria

- [ ] Preserve threshold/Important/manual eligibility, source snapshots, current validation and actual model/material provenance.
- [ ] Output contract remains media-appropriate; failed retries preserve previous successful drafts.
- [ ] Native Draft detail supports versions, compare, explicit regenerate and protected-version deletion rules.
- [ ] No new draft test-run feature or conversational editor is introduced.
- [ ] Run-bound output preferences preserve configured language/typography, immutable prior outputs and mandatory media validation; see [native-output-preferences.md](../specs/native-output-preferences.md). English text is not automatically converted to Chinese punctuation.

## Blocked by

- https://github.com/lostwildland/NoNews/issues/7
- https://github.com/lostwildland/NoNews/issues/8
- https://github.com/lostwildland/NoNews/issues/10
- https://github.com/lostwildland/NoNews/issues/11
- https://github.com/lostwildland/NoNews/issues/12

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
