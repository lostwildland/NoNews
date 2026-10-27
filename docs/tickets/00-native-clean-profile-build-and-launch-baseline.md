## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

A developer can reproducibly build and launch the native reader against an isolated acceptance profile without altering an installed NNW profile.

## Acceptance criteria

- [ ] Provide a bounded reproducible macOS build/test entry using installed Xcode; avoid mandatory private upstream secrets or interactive setup for local acceptance.
- [ ] Native app launch has its own development identity/profile; existing accounts and data in installed NNW remain untouched.
- [ ] Existing package tests and applicable build/typecheck evidence are recorded, with original failures distinguished from new ones.
- [ ] Document signing/CloudKit entitlement and simulator prerequisites without inventing a team ID; do not weaken release security to obtain a green local build.

## Blocked by

None (can start immediately).

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
