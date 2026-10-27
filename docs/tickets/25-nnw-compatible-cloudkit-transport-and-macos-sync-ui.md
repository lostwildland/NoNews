## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

A configured owner synchronizes IO data between native Mac clients with a supported transport and can understand account/offline failures.

## Acceptance criteria

- [ ] Inspect/reuse suitable NNW CloudKit sync seams; custom IO state must not piggyback unsupported third-party RSS fields.
- [ ] App entitlements/container/signing requirements and privacy are explicit; keep original account/read/star sync operational.
- [ ] Native Settings show enabling/state/error/retry, not a switch backed only by local storage.
- [ ] Transport works with real authorized accounts for acceptance; signed-out/local accounts have honest non-synced status.
- [ ] Actual draft/material availability and asset transfers are verified, not metadata-only claims.

## Blocked by

- https://github.com/lostwildland/NoNews/issues/26
- https://github.com/lostwildland/NoNews/issues/22

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
