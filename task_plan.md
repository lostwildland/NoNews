# NoNews full IO parity execution

Owner: root orchestrator. Goal: docs/goal-contract.md. Start: NNW d9ec7df; IO current source e9ba73f (dirty working tree, never assume committed snapshot is current runtime).

## Phases
- [x] Record ten answers and create durable active goal.
- [x] Publish full capability spec and 31 dependency-linked vertical tickets (90 current native edges).
- [ ] Execute frontier with one Terra high owner per ticket, isolated worktrees.
- [ ] Independent Standards/Spec review, bounded UX review, commit/push per completed ticket.
- [ ] Full personal migration, sync and live journey acceptance; reconcile matrix and final cleanup.

## Next Step
T00 is integrated and closed. T01 round-4 review found one P2 per axis: backup-path BLOB crash and missing rowid-alias semantics. Coordinator corrected both; 45 focused tests pass, including post-restore Raw creation. Fresh two-axis review follows against the original base and corrected HEAD. T02 round-2 Standards found 1 P2; Spec found 3 P2s. Coordinator fixed descriptor-failure teardown and empty historical-structure retirement at 78304d2; native controller checks and Python checks (10 pass, 1 optional skip) passed. Same owner continues bounded complete job-history reads and final bundle rebuild. Native capture still fails with cgWindowNotFound, so visible Settings Ready is unverified. Both tickets remain unaccepted; T03 stays blocked. T02 may use the serialized full Xcode resource for its next final build. Thirty tickets and the full goal remain open.

## Errors Encountered
- Initial schema search used backend/db.py (absent); actual schema entry is backend/schema.py, version 41.
- Prior ADR/journey incorrectly accepted Draft preview and required reading before integrations; corrected before implementation.
- Installed gh rejects combined --slurp/--jq; native subissue readback uses a single per_page=100 response instead.

## Constraints
No capability omissions. No production writes or private data in public repo. Use latest user decisions over older phase-downscope suggestions. No extra requirements interview. Reviews pin each ticket base. Source originals remain untouched. Only user-authorized integration targets.
