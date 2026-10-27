# NoNews full IO parity execution

Owner: root orchestrator. Goal: docs/goal-contract.md. Start: NNW d9ec7df; IO current source e9ba73f (dirty working tree, never assume committed snapshot is current runtime).

## Phases
- [x] Record ten answers and create durable active goal.
- [x] Publish full capability spec and 31 dependency-linked vertical tickets (90 current native edges).
- [ ] Execute frontier with one Terra high owner per ticket, isolated worktrees.
- [ ] Independent Standards/Spec review, bounded UX review, commit/push per completed ticket.
- [ ] Full personal migration, sync and live journey acceptance; reconcile matrix and final cleanup.

## Next Step
T00 is integrated and closed. T01 round-1 review found Standards 1 P2 and Spec 2 P1; the coordinator fixed the two narrow asset-validation defects at 1af6f75 (28 tests), while the original owner corrects WAL source-sidecar mutation before fresh review. T02 implemented and built native lifecycle/Settings at c0dbb30; its original owner now assembles the portable real-service payload and verifies the installed bundle. T03 native configuration/timing contract is prepared from actual IO source, but its T02 dependency remains unaccepted. T02 owns the serialized full Xcode resource. Thirty tickets and the full goal remain open.

## Errors Encountered
- Initial schema search used backend/db.py (absent); actual schema entry is backend/schema.py, version 41.
- Prior ADR/journey incorrectly accepted Draft preview and required reading before integrations; corrected before implementation.
- Installed gh rejects combined --slurp/--jq; native subissue readback uses a single per_page=100 response instead.

## Constraints
No capability omissions. No production writes or private data in public repo. Use latest user decisions over older phase-downscope suggestions. No extra requirements interview. Reviews pin each ticket base. Source originals remain untouched. Only user-authorized integration targets.
