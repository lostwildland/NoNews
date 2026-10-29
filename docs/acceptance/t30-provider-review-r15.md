# T30 provider and local-refresh review R15

Base `2782c51bae6f68a91baa6b86c88cc0c5fe5a1cb2`; pin `e46b1b4d03b55204f2c379c26444266168c9776d`. The assigned eight paths are Feedbin, Feedly, NewsBlur and its internal delegate, ReaderAPI, InitialFeedDownloader, LocalAccountDelegate and LocalAccountRefresher. These are source-only findings, not reproduced schedules or live-provider evidence.

## Spec

Two P2 findings:

- A second local refresh completes immediately while the earlier session still parses. Its feeds may never download, yet LocalAccountDelegate records a successful refresh date. Queue or coalesce overlapping requests truthfully and complete them only for the work they own. Preserve legitimate empty no-op behavior and each admitted request's lifetime.
- Feedbin converts non-cancellation pending-status read errors into zero reconciled changes, then stores conditional-GET metadata. A later 304 can skip the reconciliation that failed. Propagate errors for both read and starred paths; store the validator only after reconciliation succeeds.

The Spec reviewer checked all eight changed-hunk sets and ledger blobs, the nonempty original-base diff/log and whitespace. Connected reads covered account initialization/admission/drain, local download/parse ownership, status send/selection and Feedly optimistic moves. Exhaustive provider rollback/callback and live-sync coverage was not established.

## Standards

One P2: the same Feedbin error-to-zero path acknowledges an unapplied status response. No material smell verdict was possible from the partial scope.

Coverage is incomplete: Feedly and ReaderAPI diffs were only partly inspected; complete send/rollback paths, remaining local callbacks, the ledger blob readback, some concurrency guidance and latest worker evidence were not all verified. This report must not be counted as a full eight-path Standards pass. A fresh bounded assessment of the unread seams is still required.

The owner received both findings and the coverage limits. Historical full-plan results belong to their recorded source commits and do not validate the corrections in progress. No provider credentials, production accounts or remote records were accessed.
