# Native UX acceptance contract

Confirmed brief: NNW-native macOS reader with complete configurable IO functionality; Apple HIG and supported system Liquid Glass. This document is the review checklist, not proof of implementation.

## Surfaces and tasks

| Surface | Primary user task | Required behavior | Acceptance evidence |
| --- | --- | --- | --- |
| Sidebar and article list | Navigate known subscriptions and narrow attention | NNW accounts/folders/Today/Unread/Starred preserved; no new workspace requirement; current IO list information and chosen sorting | Fresh native captures and keyboard walkthrough |
| Detail | Judge, read and compare evidence | Curator first when available; real prompt output; Draft/material tabs; source vs generated text honest; current item remains after Yep | Actual news/paper/media states and interaction recording |
| Decision controls | Make or undo a personal decision | Yep stays, Nope advances in current results; no AI prerequisite; visible accessible commands independent of Star/read; undo returns a coherent state | Buttons, keyboard and gesture test, VoiceOver state announcement |
| Filters | Reuse an attention scope | Current IO condition groups, dates, removable selected conditions and saved Quick views; no extra custom Smart Feed editor | Save/apply/delete and full-result scope test |
| Settings | Configure existing power without learning backend internals | Accounts, AI services, prompts, source policies, integrations, storage and processing in native groups; advanced options discoverable; scopes/defaults/side effects visible | Clean user setup and error recovery task script |
| Integrations | Continue an established workflow | Targets selected by user; decision vs collection/adoption receipts separate; no mandatory Draft-reading gate; existing helpers work | Configured target write/readback and duplicate/modified-file cases |
| Migration | Resume a whole personal library | Preview full snapshot and mappings, show valid verification results and failures, preserve source rollback | Full local manifest, independent restore and resumed journey |
| Activity | Recover without developer logs | Real job/attention/history data, meaningful retry/cancel and progress, quiet normal state | Failure injection and public action readback |
| Sync | Continue across authorized devices | Actual content availability, settings/decision convergence and honest offline/auth state | Two-client or real-device/account evidence labelled accurately |

## Design rules

- Reuse NNW/AppKit structures, menus, toolbar idioms, inspectors, standard Settings controls and system focus behavior.
- Native Liquid Glass for supported navigation/control surfaces. Do not simulate it using pervasive CSS blur or blur reading content. Inspect SDK availability and retain native fallback on older supported systems.
- Use system semantic colors, text styles and consistent SF Symbols; active, disabled, pending and failed states must be distinguishable without color alone.
- Reading content may use the existing secure web renderer; application shell/settings/interaction must feel native rather than a transplanted FreshRSS page.
- No invented extra shell concepts, decorative counters or implementation jargon in ordinary flows. Advanced configuration retains all capabilities with clear titles and contextual explanations.
- Persist preferences and the owner's migration values rather than silently replacing them with design defaults. Explain broad shared-prompt/automation changes before applying.
- English UI consistently; display user-authored content and prompt languages faithfully.

## Required inspection matrix

All shipped macOS surfaces: light/dark, normal/narrow/wide windows, keyboard-only and VoiceOver, Reduce Transparency/Motion and state recovery. iOS companion surfaces: supported simulator/device size, larger text, safe areas and native navigation.

Native evidence must identify build SHA, target OS/device, appearance and scenario. Blank fixture screenshots cannot prove a working migration or integration. A successful source audit cannot substitute for rendered inspection.

## Bounded Impeccable finish

Build complete surfaces, inspect in one batched pass, fix the resulting material defects together, confirm with at most one further pass for that target. Separate Standards/Spec code reviews remain mandatory. Persist the resulting DESIGN record from actual shipped controls and state any live-account/device checks that remain unverified. No claim of Apple award or measured user research absent actual evidence.

## Release blockers

Missing active IO capability; data/asset loss; overwritten personal work; incorrect scope or unauthorized external side effect; broken primary keyboard/VoiceOver flow; illegible content/controls; misleading sync/migration/success state; unresolved material native-platform violation.
