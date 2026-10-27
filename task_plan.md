# NoNews full IO parity execution

Owner: root orchestrator. Goal: docs/goal-contract.md. Start: NNW d9ec7df; IO current source e9ba73f (dirty working tree, never assume committed snapshot is current runtime).

## Phases
- [x] Record ten answers and create durable active goal.
- [x] Publish full capability spec and 31 dependency-linked vertical tickets (90 current native edges).
- [ ] Execute frontier with one Terra high owner per ticket, isolated worktrees.
- [ ] Independent Standards/Spec review, bounded UX review, commit/push per completed ticket.
- [ ] Full personal migration, sync and live journey acceptance; reconcile matrix and final cleanup.

## Next Step
T00 is integrated and closed. T01 now enforces 71 required tables and 592 columns. Round 3 found one P2 per axis: malformed archive path handling (coordinator fixed at 63bf1e8; 42 tests pass) and missing semantic indexes/constraints (same owner continues). T02 final-source lifecycle/readiness/error fixes are pushed at 17fdf64; parent read the final xcresult (753 passed, zero failures) and reran Python checks (9 pass, 1 optional skip). Fresh independent round-2 review is next. Native capture still fails with cgWindowNotFound, so visible Settings Ready is unverified. Both tickets remain unaccepted; T03 stays blocked. The full Xcode resource is released. Thirty tickets and the full goal remain open.

## Errors Encountered
- Initial schema search used backend/db.py (absent); actual schema entry is backend/schema.py, version 41.
- Prior ADR/journey incorrectly accepted Draft preview and required reading before integrations; corrected before implementation.
- Installed gh rejects combined --slurp/--jq; native subissue readback uses a single per_page=100 response instead.

## Constraints
No capability omissions. No production writes or private data in public repo. Use latest user decisions over older phase-downscope suggestions. No extra requirements interview. Reviews pin each ticket base. Source originals remain untouched. Only user-authorized integration targets.
