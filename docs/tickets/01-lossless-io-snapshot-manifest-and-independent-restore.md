## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

An owner can create a consistent IO database-and-assets snapshot and restore it into an empty destination with a verifiable manifest before a native cutover.

## Acceptance criteria

- [ ] Use SQLite backup semantics for WAL/live-source consistency; source originals are never modified or removed.
- [ ] An executable public snapshot/verify/restore interface preserves every table/row and required asset with version, identity, integrity/count/hash evidence; it rejects incomplete or tampered input.
- [ ] Interrupted/repeated restore is safe and an existing destination is never silently overwritten.
- [ ] Synthetic fixtures exercise real source schema and complete round-trip restore; first ticket must not read personal body content, credentials or operate production writes.
- [ ] Record unsupported legacy forms explicitly rather than dropping them.

## Blocked by

None (can start immediately).

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
