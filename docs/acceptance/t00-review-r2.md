# T00 independent review — round 2

Base: 775500c5b007c5917d46f2461544eb4ace8e21ae
Reviewed HEAD: 62fbf30465d539bedb8819e62155a5739fcdef2f
Ticket: https://github.com/lostwildland/NoNews/issues/2
Independent Standards and Spec reviewers, both GPT-6.1 Terra high. Read-only review; no build/test/UI execution by reviewers.

## Standards

P2: snapshot-and-restore still races with another acceptance or ordinary Xcode build. Run A can generate empty source, run B snapshot it, A restore original, then B restore empty source last. Violates no-data-loss and preservation of unrelated changes. Isolate generation or coordinate all writers. Earlier sequential success/failure problem is fixed, but concurrent data loss remains.

## Spec

P2: same shared-source race can overwrite an ordinary build's newly generated source or another acceptance run's original. Source preservation is incomplete for overlapping builds. No other P1/P2 findings. This assessment is independent of Standards; the findings are not merged into a single axis.

## Response

Replaced restoration with a fresh source copy per invocation. Generation and entitlement paths point into that copy, excluding original generated keys and environment files; the original worktree is never changed by the build entry. Temporary sources are discarded after the action. A deterministic overlapping-run public test also updates ordinary source while both runs are alive: it fails against the reviewed 62fb implementation and passes for the revised implementation. Five focused test methods, shell syntax and diff checks pass.

Fix HEAD: e47d0a08f61f59510dcde68cbf7a2cb409c8cb6f, pushed to the original implementation branch. Original T00 owner is running fresh actual native build/test/launch for the changed source path before round-3 review. No ticket closure or integration yet.

Standards: 1 P2, correction pending validation/review. Spec: 1 P2, correction pending validation/review.
