# NoNews full IO parity execution

Owner: root orchestrator. Goal: docs/goal-contract.md. Start: NNW d9ec7df; IO current source e9ba73f (dirty working tree, never assume committed snapshot is current runtime).

## Phases
- [x] Record ten answers and create durable active goal.
- [x] Publish full capability spec and 31 dependency-linked vertical tickets (90 current native edges).
- [ ] Execute frontier with one Terra high owner per ticket, isolated worktrees.
- [ ] Independent Standards/Spec review, bounded UX review, commit/push per completed ticket.
- [ ] Full personal migration, sync and live journey acceptance; reconcile matrix and final cleanup.

## Next Step
T00 and T01 are accepted (2/31). T01 shared-schema corrections pass53tests and both independent R28 axes; personal migration remains unperformed. T02 code91fdf89/evidence9c9d4c8 is pushed; coordinator52total/51pass/1optionalSkip and payload/controller checks pass. Current signed relocated bundle passes identity/signature/source readback, with nine real-bundle harness passes recorded. R28 correction reviews are clear; jobs/packaging/cross-group reviews and visible UI remain open. T30 final normal build at357f463 passed, independently verified artifact identity/signature/hashes;54-path ledger splits account16/storage14/fixtures13/harness11 for manageable review. Prior769native tests remain scoped to2d1b273. Fullfeature/migration/sync/UXscope is unchanged.

## Errors Encountered
- Initial schema search used backend/db.py (absent); actual schema entry is backend/schema.py, version 41.
- Prior ADR/journey incorrectly accepted Draft preview and required reading before integrations; corrected before implementation.
- Installed gh rejects combined --slurp/--jq; native subissue readback uses a single per_page=100 response instead.

## Constraints
No capability omissions. No production writes or private data in public repo. Use latest user decisions over older phase-downscope suggestions. No extra requirements interview. Reviews pin each ticket base. Source originals remain untouched. Only user-authorized integration targets.
