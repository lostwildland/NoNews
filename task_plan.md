# NoNews full IO parity execution

Owner: root orchestrator. Goal: docs/goal-contract.md. Start: NNW d9ec7df; IO current source e9ba73f (dirty working tree, never assume committed snapshot is current runtime).

## Phases
- [x] Record ten answers and create durable active goal.
- [x] Publish full capability spec and 31 dependency-linked vertical tickets (90 current native edges).
- [ ] Execute frontier with one Terra high owner per ticket, isolated worktrees.
- [ ] Independent Standards/Spec review, bounded UX review, commit/push per completed ticket.
- [ ] Full personal migration, sync and live journey acceptance; reconcile matrix and final cleanup.

## Next Step
T02 current payload b9d2a22 has packaged validation at316e9ba; parent verified staged payload/source and relocated deep signature. Fresh R6 reviews must cover full T02 c9ecfa1..316e9ba and related root T01 follow-up09b51fa..741cbfb. T01 remains reopened and only1of31tickets is closed. T30 repair9f040dc passed99targeted/757full native tests with zero matching SQLite diagnostics, but independent R1 found Standards0/Spec2P2: failed close retry and no-new-submissions boundary. Original owner continues the complete lifecycle correction, including coordinator's small unvalidated cache fix; final native resource is available to T30. No UI visibility, personal migration/sync or overall parity acceptance is claimed. Start T03 on accepted integrated engine APIs once review/evidence gates pass.

## Errors Encountered
- Initial schema search used backend/db.py (absent); actual schema entry is backend/schema.py, version 41.
- Prior ADR/journey incorrectly accepted Draft preview and required reading before integrations; corrected before implementation.
- Installed gh rejects combined --slurp/--jq; native subissue readback uses a single per_page=100 response instead.

## Constraints
No capability omissions. No production writes or private data in public repo. Use latest user decisions over older phase-downscope suggestions. No extra requirements interview. Reviews pin each ticket base. Source originals remain untouched. Only user-authorized integration targets.
