# T30 account-core review R12

Base `2782c51bae6f68a91baa6b86c88cc0c5fe5a1cb2`; reviewed pin `8f392da024de869d3055609eaca111baa4cd7eb8`. Both independent reviewers checked the seven Account core blobs and changed-hunk sets: Account, AccountDelegate, Container, Feed, FeedSettings, Folder and OPMLFile. Provider/error/rollback implementations and exhaustive consumer call sites remain separate review work.

## Standards

Two source-derived P2 findings, not independently reproduced by the reviewer:

- A dirty OPML file retains its Account after committed deletion; saving refuses the deleted account and never clears pending ownership.
- A failed queued save consumes the one queued call. If the external owner has been released, dirty changes and the pending Account remain without a reachable retry. The existing test called back through a weak owner, masking the missing retry.

No separate material Fowler smell was established. The production deletion caller was inspected to identify the trigger; the review did not establish that deletion is otherwise safe.

## Spec

Two source-derived P2 findings, not independently reproduced by the reviewer:

- Retained Account configuration setters still write UserDefaults and emit notifications during/after closure, despite the retained-setter contract.
- Unadmitted refresh/progress state changes after close can notify and mark OPML dirty. Its pending owner then cannot save because the Account is deleted, creating a retained cycle.

The seven-path scope is not cleared. The coordinator's `e46b1b4d03b55204f2c379c26444266168c9776d` adds the shared admission guards, queued-save retry and committed-deletion ownership release. It adds/strengthens synthetic regressions for defaults, notifications, busy-close retry, admitted completion, final owner release and queued retry without accessing the Account. Only parsing/whitespace passed at handoff; the original owner is to reproduce prior behavior and run consolidated native verification. These corrections have not received fresh review.

The separate SQL correction `c13cea11f89034dbd5cf5d6055c5b7a1680d3252` now handles preparation and cached-statement iteration errors; the coordinator read its focused xcresult as 191 passed, zero failed/skipped. Those results do not cover `e46b1b4`. The prior full 786/build/iOS result remains source `0684856`. Full T30, migration/sync/UI, production deletion and live CloudKit remain open.
