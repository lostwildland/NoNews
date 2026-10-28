# T30 provider compensation review R24

This bounded Standards review is pinned to BASE `60e1f5c` and candidate `835cda3`. It read all changed hunks in the four provider status-update implementations and the connected Account, ArticlesDatabase, SyncDatabase gate, queue, refresh and send paths. It did not run tests, builds, apps, providers, CloudKit, private data or production deletion.

The review found no P1 and two source-derived P2 findings:

1. When the local status update succeeds, outbox insertion fails, and the inverse compensation also fails, the provider fallback insertion errors are discarded. If fallback insertion succeeds, the normal queue notification and sender scheduling path is skipped. The local status can therefore remain changed without a recoverable sync intent or wake-up. Preserve the fallback error and run the normal success notification path when fallback insertion succeeds.
2. The new `withStatusMutation` gate covers `markArticles`, but provider refresh and send paths still bypass it. A refresh can observe no pending local status, a user mark can commit, and stale remote state can then overwrite the local value. Extend the gate or re-read pending IDs immediately before applying remote status.

These findings remain open pending the worker correction, focused regressions and a fresh paired recheck. Historical native test totals do not clear this source boundary.
