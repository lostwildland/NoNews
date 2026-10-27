# NoNews full IO parity execution

Owner: root orchestrator. Goal: docs/goal-contract.md. Start: NNW d9ec7df; IO current source e9ba73f (dirty working tree, never assume committed snapshot is current runtime).

## Phases
- [x] Record ten answers and create durable active goal.
- [x] Publish full capability spec and 31 dependency-linked vertical tickets (90 current native edges).
- [ ] Execute frontier with one Terra high owner per ticket, isolated worktrees.
- [ ] Independent Standards/Spec review, bounded UX review, commit/push per completed ticket.
- [ ] Full personal migration, sync and live journey acceptance; reconcile matrix and final cleanup.

## Next Step
OnlyT00currentlyaccepted(1/31);T01reopenedforsharedschemafollowupwith52passingtests,narrowreviewrequired. T02guardfixes48tests47pass1skip;deepnestingstackperformanceP2stillneedsoriginalownerfix. Nativebothaxes0,DBSpecfindingsfixedbutawaitnarrowassessment;packaging/crossgroup/currentbundle/UI/remoteCIopen. T30released-ownerfix769testspassbutnormalbuildhitdiskfull;onlytwoownmodulecachesremoved(11GiB),space12GiB,andper-invocationcacheentrypasses5synthetictests. NeedfinalnativebuildandSMALLcompletegroupreviews. Fullfeature/migration/sync/UXscopeunchanged.

## Errors Encountered
- Initial schema search used backend/db.py (absent); actual schema entry is backend/schema.py, version 41.
- Prior ADR/journey incorrectly accepted Draft preview and required reading before integrations; corrected before implementation.
- Installed gh rejects combined --slurp/--jq; native subissue readback uses a single per_page=100 response instead.

## Constraints
No capability omissions. No production writes or private data in public repo. Use latest user decisions over older phase-downscope suggestions. No extra requirements interview. Reviews pin each ticket base. Source originals remain untouched. Only user-authorized integration targets.
