## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

The complete native reading and configuration journey is visually and behaviorally consistent with NNW and Apple HIG.

## Acceptance criteria

- [ ] Use standard AppKit/UIKit controls, semantic colors/SF Symbols and native Liquid Glass where supported; readable content avoids decorative glass.
- [ ] Verify light/dark, narrow/wide windows, keyboard focus/shortcuts, VoiceOver and Reduce Motion/Transparency; supported older OS has native fallback.
- [ ] One batched Impeccable inspection, one correction batch and at most one confirmation per target; fix material task-blocking/native violations.
- [ ] Capture fresh native evidence tied to commit/device/appearance and actual behavior; source-only review is not visual acceptance.
- [ ] No extra Draft previews, forced integration-after-reading gate or new workspaces appear as visual scope creep.

## Blocked by

- https://github.com/lostwildland/NoNews/issues/14
- https://github.com/lostwildland/NoNews/issues/16
- https://github.com/lostwildland/NoNews/issues/17
- https://github.com/lostwildland/NoNews/issues/20
- https://github.com/lostwildland/NoNews/issues/22
- https://github.com/lostwildland/NoNews/issues/27
- https://github.com/lostwildland/NoNews/issues/30

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
