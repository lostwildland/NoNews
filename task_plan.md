# NoNews full IO parity execution

Owner: root orchestrator. Goal: docs/goal-contract.md. Start: NNW d9ec7df; IO current source e9ba73f (dirty working tree, never assume committed snapshot is current runtime).

## Phases
- [x] Record ten answers and create durable active goal.
- [x] Publish full capability spec and 31 dependency-linked vertical tickets (90 current native edges).
- [ ] Execute frontier with one Terra high owner per ticket, isolated worktrees.
- [ ] Independent Standards/Spec review, bounded UX review, commit/push per completed ticket.
- [ ] Full personal migration, sync and live journey acceptance; reconcile matrix and final cleanup.

## Next Step
T00/T01 remain the only accepted tickets (2/31). T30 candidate209c924 passes767fulltests with zeroSQLite diagnostics and exact-host scripting binding; fresh full lifecycle/harness Standards and Spec reviews are required. T02 candidate4be1246 passes45Python tests(44pass1optionalSkip); prepare the current signed bundle and real CI evidence, then complete current-blob native/database/jobs/packaging and cross-group review. Packaging source-boundary corrections have scoped Spec0/Standards0 assessments; changed declarations still need review. API integration/T03 and full UI/migration/integration/sync acceptance remain open.

## Errors Encountered
- Initial schema search used backend/db.py (absent); actual schema entry is backend/schema.py, version 41.
- Prior ADR/journey incorrectly accepted Draft preview and required reading before integrations; corrected before implementation.
- Installed gh rejects combined --slurp/--jq; native subissue readback uses a single per_page=100 response instead.

## Constraints
No capability omissions. No production writes or private data in public repo. Use latest user decisions over older phase-downscope suggestions. No extra requirements interview. Reviews pin each ticket base. Source originals remain untouched. Only user-authorized integration targets.
