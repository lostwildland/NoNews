## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

A native subscription can be mapped to IO observations and configured for media, prompts, threshold and automation, including batch source settings.

## Acceptance criteria

- [ ] NNW articles/account/feed identities map to stable IO canonical content without changing read/star semantics.
- [ ] Five media policies, disabled/normal/Important behavior and current scope rules are retained and configurable; a new feed does not start history processing.
- [ ] One content can retain prompt-context results without duplicating shared human decisions; historical context is preserved.
- [ ] Shared setting changes disclose affected sources; job snapshots stay coherent and historical rerun requires explicit preview.
- [ ] An article appears in the native list with actual bridge data, not a separate reader.

## Implementation contract

[IO sync ownership and continuity](../specs/io-sync-ownership.md), especially canonical content versus device/account observation identity. This adds concrete checks to the existing identity/parity requirement, not runtime evidence.

[Native source identity and processing contexts](../specs/native-source-identity.md) specifies namespaced native observation bindings, independent source contexts, coherent result selection, preserved legacy pins and the public bridge checks. Current IO's single per-item pin/latest-result lookup does not already implement these requirements.

## Blocked by

- https://github.com/lostwildland/NoNews/issues/5

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
