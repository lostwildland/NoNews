# NoNews full IO parity execution

Owner: root orchestrator. Goal: docs/goal-contract.md. Start: NNW d9ec7df; IO current source e9ba73f (dirty working tree, never assume committed snapshot is current runtime).

## Phases
- [x] Record ten answers and create durable active goal.
- [x] Publish full capability spec and 31 dependency-linked vertical tickets (90 current native edges).
- [ ] Execute frontier with one Terra xhigh owner per ticket, isolated worktrees.
- [ ] Independent Standards/Spec review, bounded UX review, commit/push per completed ticket.
- [ ] Full personal migration, sync and live journey acceptance; reconcile matrix and final cleanup.

## Next Step
T00/T01/T02 remain accepted (3/31). Original owners are correcting T03 and T30 in their existing worktrees with requested Terra xhigh effort; do not overwrite unfinished source. T03 pinned `2ee43f0` now has a complete 23-path manifest and full Spec coverage (61 hunks, changes requested:3P1/1P2); paired Standards pending. Root independently reproduced completed-receipt endpoint mismatch via authenticated stdio. T30 pinned `835cda3` has a complete 109-path manifest; paired R24 finds two provider durability/reconciliation defects (worst P1). Next, validate the owners' corrected public regressions and strict current-source checks, then commission fresh paired rechecks against clean pins. Final artifact/platform/HIG/Keychain/live integration/personal migration/complete feature acceptance remains open. No new worktrees, broad cleanup, privacy repair or acceptance-count change.

## Errors Encountered
- T03 narrow preferences typecheck depended on maps referencing a removed private source copy. Temporary maps to matching accepted headers resolved missing RSDatabaseObjC; a one-line MainActor fix then passed warnings-as-errors. No shared cache/map or dependency was modified.
- R18 T30 provider turn failed503 before delivery. Preserved all unfinished edits and resumed the same owner; user explicitly excluded local masking-model repair. No protection setting or provider was changed.
- Some combined inspection output was truncated; only bounded readable portions count as review coverage. A tracker inspection assumed a list instead of its keyed ticket dictionary; the corrected read used the dictionary keys.
- T03 ordinal2 provider turn failed; actual worktree retains a719dd3 plus uncommitted configuration/native/migration work. Same owner resumed, without discarding edits or guessing a disk-related cause.
- Script-inventory recheck found two changed source hashes; regenerated the inventory and independently reread all106 entries before publication.
- Initial schema search used backend/db.py (absent); actual schema entry is backend/schema.py, version 41.
- Prior ADR/journey incorrectly accepted Draft preview and required reading before integrations; corrected before implementation.
- Installed gh rejects combined --slurp/--jq; native subissue readback uses a single per_page=100 response instead.

## Constraints
UI and interaction work must consult Apple's official Human Interface Guidelines (HIG) during design and development, then record applicable guidance and verify native behavior at review/acceptance; see docs/goal-contract.md and docs/acceptance/native-ux-contract.md. User reaffirmed this requirement on 2026-10-28.

T03 source audit at6da5efa found unscoped editor responses can select a service/target different from the visible form. The same owner received the concrete stale-binding, prompt-load and shared-save schedules during R12. Complete matching-intent guards and actual controller/request regressions along with cooperative operations before final native acceptance; do not count migration-only state checks as coverage of general forms.

No capability omissions. No production writes or private data in public repo. Use latest user decisions over older phase-downscope suggestions. No extra requirements interview. Reviews pin each ticket base. Source originals remain untouched. Only user-authorized integration targets.
