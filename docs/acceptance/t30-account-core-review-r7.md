# T30 account-core review — round 7

Original base: `2782c51bae6f68a91baa6b86c88cc0c5fe5a1cb2`. Reviewed HEAD: `7accb68382f80c0d4b48c922c8b81899f0364b57`; source: `6f849ae92744873a576eeaff049191e5be5690d6`.

Both axes checked the seven core path blobs and changed-hunk sets: Account, AccountDelegate, Container, Feed, FeedSettings, Folder and OPMLFile. Principal lifecycle, permit, callback, setter and OPML paths and new refresh/context tests were examined. Full connected service-delegate asynchronous/error/rollback paths remain incomplete, so this is not an account-scope pass or T30 acceptance.

## Standards

One source-derived P2: weak OPML/account ownership and a weak coalesced-save target can release an accepted dirty subscription change before its queued write. Preserve pending save ownership until a successful write, then release it. No additional material Standards-only finding was reported.

## Spec

Two source-derived P2 findings: the multi-database vacuum is not admitted as a whole and can lose its later stages during close; public CloudKit cleanup bypasses admission/drain, allowing an in-flight operation to outlive owned removal or a new operation after closure. Neither was runtime-reproduced by the reviewers.

## Coordinator correction and required continuation

The coordinator added temporary pending-save Account ownership to OPMLFile, released after successful flush, and wrapped the whole vacuum and CloudKit cleanup in the existing operation admission. The matching public CloudKit stats read uses the same lifecycle boundary. These small changes are uncommitted in the original owner's worktree and have only passed whitespace checks. The sole T30 owner is reproducing the reviewed schedules and validating the correction, including owner release before queued save, failed-save retry and admitted maintenance drain. Existing released-owner setters must still be tested with a clean owner released without closing first.

The coordinator independently read the R11 xcresult: 771 passed, zero failed/skipped and 296 parameterized runs. The recorded action log has zero disk-I/O or vnode-unlink matches, and the normal artifact's isolation and deep strict signature pass. These results apply to `6f849ae`; they do not validate the new uncommitted correction. The generic scripting main-thread warning remains unresolved. Storage, fixtures, harness, service delegates and full T30/migration/sync/UI acceptance remain open.
