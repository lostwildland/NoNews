# NoNews full IO parity execution

Owner: root orchestrator. Goal: docs/goal-contract.md. Start: NNW d9ec7df; IO current source e9ba73f (dirty working tree, never assume committed snapshot is current runtime).

## Phases
- [x] Record ten answers and create durable active goal.
- [x] Publish full capability spec and 31 dependency-linked vertical tickets (90 current native edges).
- [ ] Execute frontier with one Terra high owner per ticket, isolated worktrees.
- [ ] Independent Standards/Spec review, bounded UX review, commit/push per completed ticket.
- [ ] Full personal migration, sync and live journey acceptance; reconcile matrix and final cleanup.

## Next Step
Only T00 is currently accepted (1/31). T01's quoted-BINARY follow-up passes 53 snapshot tests and needs narrow two-axis review before reacceptance. T02 is pushed at 3c9c2e7: cached parser owner reports about 0.8s first frames, coordinator final Python suite passes 50 tests with one optional skip, payload/controller checks pass. Shared schema/helper, jobs performance, current packaging and cross-group reviews and current installed-bundle/UI acceptance remain open. T30 is at 357f463 with 769 prior native passes; final-source normal build after cache recovery and smaller complete review scopes are next. Full feature, personal migration, sync and UX scope is unchanged.

## Errors Encountered
- Initial schema search used backend/db.py (absent); actual schema entry is backend/schema.py, version 41.
- Prior ADR/journey incorrectly accepted Draft preview and required reading before integrations; corrected before implementation.
- Installed gh rejects combined --slurp/--jq; native subissue readback uses a single per_page=100 response instead.

## Constraints
No capability omissions. No production writes or private data in public repo. Use latest user decisions over older phase-downscope suggestions. No extra requirements interview. Reviews pin each ticket base. Source originals remain untouched. Only user-authorized integration targets.
