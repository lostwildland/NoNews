## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

An editor adopts a specific News/Paper draft into a configured existing issue and can verify usage across existing external workflows.

## Acceptance criteria

- [ ] Preserve eligible existing issue selection and draft/image/type gates; do not create issues implicitly or equate adoption with public publishing.
- [ ] Intent/receipt pins canonical content/version/issue identity, avoids duplicate blocks and requires explicit hash-checked replacement.
- [ ] External macros/spool/catch-up update the shared ledger without importing private body text into status records.
- [ ] Native status shows pending/verified/unknown appropriately; new drafts never silently overwrite adopted versions.

## Blocked by

- https://github.com/lostwildland/NoNews/issues/13
- https://github.com/lostwildland/NoNews/issues/19

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
