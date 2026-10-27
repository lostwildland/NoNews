## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

An iPhone running the shared app can resume synchronized Curator/Draft/material reading and judgments while preserving NNW mobile behavior.

## Acceptance criteria

- [ ] Shared sync records/settings/results and Yep/Nope are consumed with real account boundary handling.
- [ ] iOS build remains green; native navigation, safe areas, text scaling and accessibility match Apple conventions.
- [ ] Missing/offline assets are explicit; no device pretends that reading metadata proves complete content transfer.
- [ ] Two-client/device continuity and original read/star sync are evidenced; unavailable physical-account checks remain pending.

## Implementation contract

[IO sync ownership and continuity](../specs/io-sync-ownership.md). Exercise actual Draft/material bytes, an unavailable source account and device-specific credentials/access; metadata arrival alone is not readable/offline continuity.

## Blocked by

- https://github.com/lostwildland/NoNews/issues/27
- https://github.com/lostwildland/NoNews/issues/14

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
