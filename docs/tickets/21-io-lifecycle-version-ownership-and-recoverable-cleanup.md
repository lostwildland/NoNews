## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

An owner uses existing IO retention/recovery behavior safely alongside NNW cache cleanup and can configure personal cleanup preferences.

## Acceptance criteria

- [ ] Existing database/file-authority boundaries, immutable versions and checksum checks remain; NNW article eviction cannot silently delete IO evidence.
- [ ] Preserve seven-day reject recovery and Select rescue when enabled, protected references and independent backup-readback requirements.
- [ ] Storage settings explain scope; cleanup leaves required identity/audit/tombstones, and external copies are not blindly deleted.
- [ ] Restore/failed-cleanup/late-write scenarios are verifiable through public operations.

## Blocked by

- https://github.com/lostwildland/NoNews/issues/3
- https://github.com/lostwildland/NoNews/issues/15
- https://github.com/lostwildland/NoNews/issues/21

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
