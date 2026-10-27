## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

Two separately stored clients synchronize IO settings, decisions and result references with durable retry and deterministic merge behavior.

## Acceptance criteria

- [ ] Use stable content/context identities; preserve versions/intents/receipts and protected assets without secret synchronization in ordinary records.
- [ ] Offline outbox, acknowledgments, conflicts, deletions/tombstones and duplicate delivery converge and survive restart.
- [ ] Reject precedence and adopted-version protection survive delayed remote operations; do not duplicate paid work on replay.
- [ ] Tests exercise actual persistent public adapters; fake transport tests are labeled separately from cloud verification.

## Implementation contract

[IO sync ownership and continuity](../specs/io-sync-ownership.md). Preserve execution ownership, causal decision guards and receipt evidence; replication alone must not replay paid or external work. Its public schedules supplement the existing persistent two-client checks.

## Blocked by

- https://github.com/lostwildland/NoNews/issues/6
- https://github.com/lostwildland/NoNews/issues/15
- https://github.com/lostwildland/NoNews/issues/23

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
