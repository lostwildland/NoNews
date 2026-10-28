# NoNews full IO parity execution

Owner: root orchestrator. Goal: docs/goal-contract.md. Start: NNW d9ec7df; IO current source e9ba73f (dirty working tree, never assume committed snapshot is current runtime).

## Phases
- [x] Record ten answers and create durable active goal.
- [x] Publish full capability spec and 31 dependency-linked vertical tickets (90 current native edges).
- [ ] Execute frontier with one Terra high owner per ticket, isolated worktrees.
- [ ] Independent Standards/Spec review, bounded UX review, commit/push per completed ticket.
- [ ] Full personal migration, sync and live journey acceptance; reconcile matrix and final cleanup.

## Next Step
T00/T01 accepted (2/31). T02 R29 jobs/controller reviews completed9/9 on both axes: valid12MB broad arrays and16MB very-deep records exceed request deadlines. Capacity error fixed atd36d44a with52total/51pass/1optionalSkip; implement bounded cooperative preparation through existing cursor without reducing512MiB capacity, source semantics or memory coverage. R11 artifact is historical; current bundle/review/UI gates remain. T30 final build passed at357f463; review account16/storage14/fixtures13/harness11 groups against857cadd, keeping fullT30/migration/sync/UX open.

## Errors Encountered
- Initial schema search used backend/db.py (absent); actual schema entry is backend/schema.py, version 41.
- Prior ADR/journey incorrectly accepted Draft preview and required reading before integrations; corrected before implementation.
- Installed gh rejects combined --slurp/--jq; native subissue readback uses a single per_page=100 response instead.

## Constraints
No capability omissions. No production writes or private data in public repo. Use latest user decisions over older phase-downscope suggestions. No extra requirements interview. Reviews pin each ticket base. Source originals remain untouched. Only user-authorized integration targets.
