## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

The native app starts and stops a private IO processing component and shows its real availability without requiring a separately deployed personal backend.

## Acceptance criteria

- [ ] Use existing IO observable contracts and sanitized reusable source where possible; no unrelated FreshRSS runtime requirement.
- [ ] Provide authenticated private command/read communication, app-managed data locations and lifecycle/error recovery.
- [ ] Native status differentiates launching, ready, failed and stopped; merely displaying a stub is insufficient.
- [ ] No personal paths, account identifiers, keys or acceptance-only gates are embedded in public shipping code.
- [ ] Packaging declares Python/native dependencies and licensing; an actual installed-bundle smoke check proves runtime discovery.

## Blocked by

- https://github.com/lostwildland/NoNews/issues/2

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
