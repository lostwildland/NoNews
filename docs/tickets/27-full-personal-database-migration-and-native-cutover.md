## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

The existing owner imports the entire verified IO database/assets/configuration, maps sources and resumes the complete workflow in NoNews.

## Acceptance criteria

- [ ] Native importer previews the complete snapshot and destination/source mappings, validates version/integrity/space and reports every retained/unmapped asset.
- [ ] All rows, histories, versions, decisions, settings, bindings, jobs, collection/adoption/receipts and legacy references are accounted for; no sample-only substitute.
- [ ] Historical import is passive: no model runs, collection or adoption replay without explicit post-import action.
- [ ] Full private-data reconciliation and independent restore evidence are local/redacted; source system remains intact and rollback demonstrable.
- [ ] Resumed native workflow is exercised against actual authorized services without overwriting existing personal work.

## Blocked by

- https://github.com/lostwildland/NoNews/issues/3
- https://github.com/lostwildland/NoNews/issues/14
- https://github.com/lostwildland/NoNews/issues/18
- https://github.com/lostwildland/NoNews/issues/19
- https://github.com/lostwildland/NoNews/issues/20
- https://github.com/lostwildland/NoNews/issues/23
- https://github.com/lostwildland/NoNews/issues/24
- https://github.com/lostwildland/NoNews/issues/25
- https://github.com/lostwildland/NoNews/issues/27

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
