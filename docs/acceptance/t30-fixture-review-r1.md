# T30 fixture repair independent review — round 1

Base: `2782c51bae6f68a91baa6b86c88cc0c5fe5a1cb2`  
Reviewed HEAD: `9f040dcef27b6665d49bfc18db97a2d745de2ac5`

This is the fixture-lifetime repair slice of issue #32, not full T30 or parity acceptance.

## Standards

0 actionable P1/P2 findings; worst severity none. The independent reviewer confirmed both refs, two commits, the nonempty 32-file diff and whitespace check. It inspected shared lifecycle/database changes, fixture callers, regressions and the issue. Its additional Spec statement does not replace the separate Spec assessment below.

## Spec

2 P2 findings. First, Account caches a failed close task, so a later deletion attempt cannot retry a retained busy SQLite handle. Second, closing does not establish a no-new-submissions boundary: retained Feed setters, article database operations and direct account reads can submit work after closure, outside the awaited drain.

Both findings are supported by the connected source paths. The coordinator cleared the failed cached task inside its completion on the owning actor; that small correction remains uncommitted and unvalidated in the T30 worktree for the original owner to cover with an owner-path retry regression. The original owner must implement the complete submission boundary with coherent callback/async rejection and preserve already accepted work. Do not solve this by dropping callbacks or weakening functional tests.

## Evidence limits and next validation

The prior 99 targeted and 757 full native passes, and the parent's extraction of zero disk-I/O/unlink lines, remain evidence for the reviewed HEAD only. Neither reviewer reran those suites. Revised code needs behavioral retry and post-close submission tests, final native validation and fresh independent two-axis review. Production account deletion, migration, sync, UI and full T30 remain unaccepted.

## Original-owner continuation checkpoint

Owner HEAD `74a65617b399dc7ace96f34c7c401fca9da7aa9a` adds a real busy SQLite backup/account-owner regression, concurrent close callers, retained directory/inode on failure and successful retry/removal. That focused test passed in the recorded `2026.10.28_04-09-00` result bundle; it covers the coordinator's retry correction at the intended owner boundary.

The complete admission boundary remains unimplemented. The enabled `retainedFeedRejectsChangesAfterClose` regression is still red, and the owner did not rerun the full plan. This pushed checkpoint is not accepted or integrated. The root has clarified the existing nonthrowing-read, setter and callback refusal behavior in the T30 ticket so the same owner can finish the repair without another requirements interview. No external blocker has been established.
