## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

A reader collects supported media into a configured Zotero target with existing ownership safeguards and verified status.

## Acceptance criteria

- [ ] Preserve explicit intent eligibility; auto high score and Accept AI alone do not become collection commands.
- [ ] Correct media parents/attachments/notes and identity resolution retain current behavior.
- [ ] Never overwrite user notes/annotations or claim a near-title record; external target and optional Yep linkage are configurable.
- [ ] Native status separates decision, queued/failed collection and readback-confirmed success.
- [ ] Fixtures prove idempotency/ownership; live isolated readback evidence is reported separately.

## Blocked by

- https://github.com/lostwildland/NoNews/issues/13
- https://github.com/lostwildland/NoNews/issues/15

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
