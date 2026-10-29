# T30 provider compensation review R24

Fixed BASE `60e1f5c`, candidate `835cda3`. Both reviewers read every changed provider hunk (Feedbin, Feedly, NewsBlur and ReaderAPI) plus connected Account, article status, sync transaction/gate, refresh/send and CloudKit acknowledgement paths. No tests, builds, app, live provider/CloudKit, private data or production deletion were run.

The axes identify **two overlapping underlying defects**, not four independent bugs. Standards reports two P2s; Spec reports one P1 and one P2. Worst severity is P1.

1. **Outbox intent is not preserved through double failure (Spec P1; Standards P2).** After local article status commits, queue insertion can fail, inverse compensation can fail, and a fallback `try? insertStatusesOrThrow` can also fail silently. CloudKit lacks an equivalent fallback. A successful provider fallback also skips normal queue notification/scheduling. Preserve a durable retryable intent or the prior local state, retain actual fallback errors and recovery status, and run normal scheduling after successful fallback. Merely reporting an error does not make an unsynced local mutation durable.
2. **Remote reconciliation can overwrite a newer local mark (P2).** The providers snapshot pending IDs outside `withStatusMutation`, then later apply remote status. A newer local action can arrive between those steps. After the network response, read pending IDs, calculate the diff and apply local status under the shared gate; do not hold that gate across network fetches. Inspect sender claim/deletion interactions with compensation as part of the correction.

Both findings are source-derived and were not reproduced by the reviewers. They remain open until the worker publishes a clean correction with deterministic regressions and a fresh paired recheck. Historical native test totals do not clear this source boundary or establish full T30 acceptance.
