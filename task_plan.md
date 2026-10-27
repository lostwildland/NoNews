# NoNews full IO parity execution

Owner: root orchestrator. Goal: docs/goal-contract.md. Start: NNW d9ec7df; IO current source e9ba73f (dirty working tree, never assume committed snapshot is current runtime).

## Phases
- [x] Record ten answers and create durable active goal.
- [x] Publish full capability spec and 31 dependency-linked vertical tickets (90 current native edges).
- [ ] Execute frontier with one Terra high owner per ticket, isolated worktrees.
- [ ] Independent Standards/Spec review, bounded UX review, commit/push per completed ticket.
- [ ] Full personal migration, sync and live journey acceptance; reconcile matrix and final cleanup.

## Next Step
T02 R5 conflict-policy fix b9d2a22 and related root T01 follow-up741cbfb pass19engine tests(18pass1skip), controller checks and51snapshot tests. T01 issue3 is reopened until the related independent review passes;1of31tickets closed. T02 current payload needs packaged verification, then R6 review covering full T02 original-base range plus root09b51fa..741cbfb follow-up. T30 fixture repair9f040dc passed99targeted/757full native tests; parent confirms actual757pass0fail0skip and zero matching SQLite diagnostics in9470emittedlines. Repair-only independent reviews pending; full T30 remains open. T30 released the heavyweight resource; it can now be reserved for T02 packaging. No UI visibility, personal migration/sync or overall parity acceptance is claimed.

## Errors Encountered
- Initial schema search used backend/db.py (absent); actual schema entry is backend/schema.py, version 41.
- Prior ADR/journey incorrectly accepted Draft preview and required reading before integrations; corrected before implementation.
- Installed gh rejects combined --slurp/--jq; native subissue readback uses a single per_page=100 response instead.

## Constraints
No capability omissions. No production writes or private data in public repo. Use latest user decisions over older phase-downscope suggestions. No extra requirements interview. Reviews pin each ticket base. Source originals remain untouched. Only user-authorized integration targets.
