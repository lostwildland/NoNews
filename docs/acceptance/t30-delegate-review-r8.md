# T30 service-delegate review — round 8

Original base: `2782c51bae6f68a91baa6b86c88cc0c5fe5a1cb2`. Pinned review source: `7accb68382f80c0d4b48c922c8b81899f0364b57`. Both axes verified all nine service-delegate changed-hunk sets and pinned path blobs. This is not complete service-delegate clearance: CloudKit zone callbacks and portions of remote-provider network/error/rollback seams remain unreviewed or truncated. Those omissions remain explicit review work.

## Standards

One source-derived P2, not runtime-reproduced by the reviewer: delayed refresh setup permits two calls past the local progress check. A later empty/skipped refresh can replace the active download's `refreshWork`, then finish its own permit. On close, the original download's metadata and parse can be rejected under that expired permit.

## Spec

One source-derived P2, not runtime-reproduced by the reviewer: session completion schedules a task that later reads the mutable completion property. A newly started refresh can replace it before that task runs, causing the old session to complete and clear the new refresh's continuation instead of its own. Closing can then cancel work whose caller has already been resumed.

Both concern the requirement to drain admitted operations and their dependent URLSession, parse and database work. They are distinct schedules sharing mutable refresh ownership.

## Coordinator correction and validation boundary

The coordinator inspected all refresher callers and DownloadSession completion/progress ordering, then changed only LocalAccountRefresher: initial continuation setup runs immediately on its existing main actor; a duplicate in-flight setup returns before replacing the active work, counters or URL mapping; the obsolete replacement-completion path is removed; and session completion captures and clears its matching callback before scheduling it. Session identity is checked as in the other admitted callback paths.

Whitespace checks pass, but this correction is uncommitted and has no behavioral acceptance yet. It was steered to the sole existing T30 owner, alongside the R12 pending-save/maintenance regressions, for deterministic baseline reproduction of both schedules and final focused/full/native validation. A build already in progress retains its earlier source boundary; it is not proof for this later edit. No live feeds, CloudKit or private data are authorized by these synthetic tests.

The original 771-pass result remains evidence for `6f849ae`, not this correction. Storage, fixtures, harness, remaining provider seams and whole T30/migration/sync/UI acceptance remain open.
