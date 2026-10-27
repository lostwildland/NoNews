# IO sync ownership and continuity contract

Implementation contract for T04/T13/T21/T24–T26 under the accepted full-parity goal. It makes existing preservation and sync requirements concrete; it is not a functioning transport or runtime acceptance. Source inspection: 2026-10-28, NoNews `5544e9d`, reference IO dirty working tree at `e9ba73f`. No account, credential or personal library was accessed.

## Separate the two sync responsibilities

NNW accounts retain their subscription, read/unread and Star behavior. IO settings, human decisions, processing contexts, versions, receipts and retained materials use a supported private NoNews channel. Neither successful RSS-account sync nor a normal account icon proves IO data has transferred. Signed-out, offline, unavailable-container and credential-required states are visible without blocking ordinary reading.

The same canonical content can be observed through different accounts/providers and on different devices. Preserve every observation-to-content mapping and the original imported identifiers. NNW article IDs, local account IDs and SQL row numbers alone do not establish global content identity. Use the T04 identity bridge and verified DOI/arXiv/video/normalized-URL identities where supported; preserve unresolved observations rather than merging by title. Independently created records for the same verified content must converge without losing their separate prompt contexts or histories.

No IO fields are encoded as synthetic read/Star changes. Local-only RSS accounts remain local-only for those original account facts even if the user separately enables IO sync. iOS may display a synchronized IO item whose original RSS account or cached article is unavailable; show the available retained content and an honest source-availability state.

## Preserve content independently of RSS caches

NNW's Articles zone can delete content records when an article becomes read or unstarred under its existing policy. Those deletions do not authorize deleting IO bodies, drafts, imported file authority, history, collection/adoption receipts or protected assets. Conversely, an IO Nope is not authority to delete a remote Zotero item or NNW subscription.

Sync a result with its content/context/version identity, immutable content hash, material evidence and prompt/model provenance. Its readable bytes must actually be available to the receiving client or explicitly pending/unavailable; a URL, version row or asset hash alone is insufficient. Transfer assets through a bounded verified path, retain protected/adopted versions and apply the T21 lifecycle and recovery deadlines. Cache eviction and logical deletion are different operations. Metadata may arrive before bytes, but the UI must not label that state fully available offline.

Device-specific absolute vault/staging paths and file identities cannot become working paths on another device. Preserve their origin evidence; obtain destination mappings and access on that device before local file operations. Never walk an entire unrelated vault because an asset's parent root was selected. File-authority conversion still requires the separately verified migration/ownership path.

## Data replication does not replay execution

Retain jobs, intents and receipts as evidence, including imported work. Receiving these records or reconnecting must not itself drain a remote queue, run a model, upload media, collect in Zotero, export into a vault or adopt an issue. Sync application and explicit execution are separate public operations. A job's pending state on its execution device is not permission for every replica to execute it.

Preserve operation identity, origin, target and outcome so duplicate delivery is a no-op. Before any cross-device processing/side-effect execution, establish one authorized execution owner and recheck current decision/material/target guards; takeover cannot silently duplicate an uncertain previous external write. Do not invent a new attempt because an acknowledgment was lost. Reconcile uncertain outcomes with the configured external target through the existing receipt/intent workflow. An imported job is passive until the explicit post-import activation boundary; preserve its fields rather than rewriting it cancelled to achieve passivity.

Synced prompt/service configuration preserves the explicit requested service/model or Magpie target. Credentials remain in secure device storage and outside ordinary sync records. If a device lacks the matching credential or configured integration access, retain the binding and show it unavailable; do not substitute a provider, inherit a default or copy a foreign Keychain reference as though it were usable. Saving or receiving configuration performs no inference.

## Offline decisions and delayed writes

Retain decision event identities and causal context; independent device counters and wall clocks alone cannot determine a shared authorization generation. Concurrent Nope and an older/unobserved Yep resolve with Nope taking precedence, as T24 requires. A deliberate later Yep that has observed that Nope can restore selection through the normal IO command semantics. Nope must not become an irreversible permanent preference.

Apply each remote decision once. A newly applied Nope invalidates local queued/running work through the same cancellation/generation guards as a local decision; delayed body/draft writes still fail. A later Yep permits newly authorized work and does not revive work admitted before either decision. Preserve existing completed external collection/adoption facts. Syncing a decision is not an external success receipt or an instruction to repeat an already completed collection.

Deletion/tombstones retain the identity and causal evidence needed to prevent stale replicas from resurrecting removed state. Protected-version and recovery rules remain effective during merge and garbage collection. A newer unsupported record/schema remains retained and visibly incompatible; do not discard fields or silently reset the library to make the clients agree.

## Required public checks

T04/T24 jointly exercise two distinct persisted client stores observing the same canonical content through different account/article IDs, plus two different contents with the same title. Verify one shared decision, preserved observations and independent processing contexts; repeat after restart and duplicate delivery.

T13/T21/T24 exercise this schedule: A admits work, B goes offline and records Yep, A records Nope, then B's stale event and the old job result arrive. The stale event/result cannot restore content or external intent. After B receives the Nope, a deliberate fresh Yep can select again, and only newly admitted work may write. Check history, local guard generations and protected receipts as well as the final visible state.

T24/T25 exercise an interrupted transfer, duplicate acknowledgment, restart and separately stored outboxes with queued jobs/intents on both sides. Applying sync alone produces zero model/integration writes. Verify execution ownership and uncertain-receipt recovery at the actual public boundary used by the runner. Simulated transport evidence is labelled separately from real CloudKit.

T25/T26 exercise read/unstar/cache cleanup independently of retained IO versions, full Draft/material bytes on the second client, an unavailable original RSS account, missing device credentials/vault mapping, sign-out/account change and an offline tombstone. Original NNW read/Star tests remain in place. Real authorized CloudKit/device and iOS build evidence are required by their tickets; an acceptance-profile build without iCloud entitlements cannot supply it.

## Reuse evidence and limits

- `Modules/Account/Sources/Account/CloudKit/CloudKitAccountDelegate.swift`: account-scoped container, account availability handling, refresh/send orchestration and Activity integration. These are reusable patterns, not a public custom-data hook.
- `CloudKitAccountZone.swift` and `CloudKitArticlesZone.swift`: separate private Account/Articles zones. ArticleStatus fields are feed external identity, read and Star; makeArticleRecord carries RSS content. No IO decision/context/version fields are currently present.
- `CloudKitArticlesZone.modifyArticles` and `shouldDeleteContentRecord`: content upload/cleanup depends on read/Star/unread-content policy, and status/content sends are separated so a content failure does not block statuses. Do not attach retained IO lifetime to that record.
- `Modules/SyncDatabase/Sources/SyncDatabase/SyncDatabase.swift` and `SyncStatusTable.swift`: original queue key is articleID/status-key; acknowledgment/reset operates on selected statuses. It is not already an IO event/version/asset outbox.
- `Mac/Resources/NetNewsWire.entitlements`: production CloudKit container uses the configured organization identifier. `buildscripts/acceptance.entitlements` deliberately lacks iCloud entitlement; isolated tests do not prove production provisioning or sync.
- Reference IO `backend/core.py`: `identity_for`, `_review`, `assert_content_write_allowed` preserve canonical identity, idempotent human events, rejection withdrawal/cancellation, cleanup request and local generation guards. `backend/jobs.py` retains job operation/origin/generation evidence. Cross-device merge is new work; do not present these local counters as an implemented global ordering protocol.

Inspected source-byte SHA-256: IO `backend/core.py` `17c00866752ad7fea41b44d5be39703c8553f9b4afcfa3e8a91f2cf28683293e`; `backend/jobs.py` `11e0ede95a8379a7ed62f57713f41302b4f2a4744ff17a2e8866a03df16081e1`. The dirty checkout HEAD alone does not identify those files' bytes.

No new cloud container, account, entitlement grant or remote record was created during this investigation. T24/T25 owners must document the actual supported private transport and record/asset format, provision only authorized identities and verify the complete journey. A CloudKit type or manifest in source is not evidence of live-account success.
