# NoNews full IO parity execution

Owner: root orchestrator. Goal: docs/goal-contract.md. Start: NNW d9ec7df; IO current source e9ba73f (dirty working tree, never assume committed snapshot is current runtime).

## Phases
- [x] Record ten answers and create durable active goal.
- [x] Publish full capability spec and 31 dependency-linked vertical tickets (90 current native edges).
- [ ] Execute frontier with one Terra high owner per ticket, isolated worktrees.
- [ ] Independent Standards/Spec review, bounded UX review, commit/push per completed ticket.
- [ ] Full personal migration, sync and live journey acceptance; reconcile matrix and final cleanup.

## Next Step
T00 is integrated and closed. T01 fixed the WAL source boundary; round 2 found incomplete-schema acceptance, imported-Raw authority and corrupt-gzip handling. The coordinator fixed the two narrow Raw/gzip defects (37 tests); the original owner implements canonical structure checks and complete fixtures. T02 has a relocated bundled real schema/service slice; round 1 found historical-data retirement, child ownership, readiness overflow and opaque errors. The coordinator guarded historical startup (7 passing tests, 1 optional skip after refreshing a stale stage); the original owner fixes lifecycle/readiness/errors and rebuilds. Both tickets remain unaccepted. T03 remains blocked. T02 owns the serialized full Xcode resource. Thirty tickets and the full goal remain open.

## Errors Encountered
- Initial schema search used backend/db.py (absent); actual schema entry is backend/schema.py, version 41.
- Prior ADR/journey incorrectly accepted Draft preview and required reading before integrations; corrected before implementation.
- Installed gh rejects combined --slurp/--jq; native subissue readback uses a single per_page=100 response instead.

## Constraints
No capability omissions. No production writes or private data in public repo. Use latest user decisions over older phase-downscope suggestions. No extra requirements interview. Reviews pin each ticket base. Source originals remain untouched. Only user-authorized integration targets.
