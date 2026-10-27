## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

A paper displays identity-validated abstract-based Curator output or an honest missing/candidate/error state.

## Acceptance criteria

- [ ] Publisher/arXiv/catalog routes retain existing identity/completeness/provenance validation and available/candidate/missing distinctions.
- [ ] No full-text fallback silently replaces a missing abstract for scoring; title-only and correction rules retain source behavior.
- [ ] Native Abstract and Curator layers show the right material and result.
- [ ] Regression fixtures include mismatched DOI/title, truncated abstract and valid identity.

## Blocked by

- https://github.com/lostwildland/NoNews/issues/6

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
