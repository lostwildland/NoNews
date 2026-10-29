## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

A reader explicitly creates/opens an Obsidian working copy without overwriting personal edits and can keep the existing Zotero helper path.

## Acceptance criteria

- [ ] Configured vault/paths replace personal hardcodes; existing native action/helper compatibility remains.
- [ ] Missing body creates no empty note; repeat exports protect user modifications; explicit rebuild handles missing files.
- [ ] Navigation-only badges do not auto-create files; Zotero full-text linkage is verified where applicable.
- [ ] Native action and helper round-trip are tested at the public integration boundary.

## Blocked by

- https://github.com/lostwildland/NoNews/issues/9
- https://github.com/lostwildland/NoNews/issues/18

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
