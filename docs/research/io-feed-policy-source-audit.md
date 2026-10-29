# IO feed-policy behavior for T04

Read-only source inspection on2026-10-28. This prepares the existing T04 scope; it is not NoNews implementation, a live FreshRSS check or personal-settings migration. Reference checkout HEAD `e9ba73f0b44a781ea68c0670114f9281f66f5cd3` is dirty. No source module was executed/imported and no personal database, prompt, configuration or credential was read.

## Observed contract

The source authority is `backend/feed_settings.py`, not folder placement. `ai_feed_settings` stores processing mode, fixed media, legacy Kit ID, separate scoring/body strategies, authored-origin evidence and subscription-list observations. `item_feed_contracts` stores admission pins; `item_material_fingerprints` records the independently acquired scoring/body evidence.

| Source fact | Required preservation in NoNews |
| --- | --- |
| Modes are disabled, normal and important; an unconfigured source starts disabled | Add a subscription without starting AI or historical processing. Preserve imported choices; ordinary reading stays available. |
| Enabled processing requires a fixed supported media type and compatible Kit; auto media is refused | Keep five explicit media contracts. Native prompts bind their own service/target as already chosen by the user; no hidden model inheritance or fallback. Retain legacy Kit IDs/provenance during migration rather than making Kit selection an extra mandatory native concept. |
| Scoring and body acquisition are different roles | A failed scoring route yields no fabricated score. A later body failure stays distinct, preserves a valid earlier score and cannot become an empty successful Draft. |
| Important can continue after a recorded low score | Preserve the score, reason and decision. It cannot override human Nope, missing/invalid scoring material or title-only Paper evidence, and does not manufacture a human Yep or collection/adoption eligibility. Keep it separate from NNW Star/read. |
| Current disabled mode blocks automatic spending stages | Stop later automatic model/network stages even for an old pin. Explicit manual actions still follow their own material, identity and authorization checks. |
| Folder/title metadata is not routing | Moving or renaming folders must not change prompts, threshold, media or acquisition. A folder may select a bulk-edit scope without becoming inheritance. |
| Subscription state and IO lifecycle are separate evidence | Subscribed/missing/unverified does not itself enable/disable processing or authorize deleting retained IO content; do not equate an uncertain empty listing with removal. |
| Authored, history and unset origins differ | Preserve deliberate null/cleared settings; reconciliation or legacy folder migration must not fill them back in as though the source were never configured. |
| Source edits do not rewrite admission pins or historical results | Apply the already specified admission/run/rerun/queued-Editor boundaries within independent source contexts. |
| Legacy bulk save changes processing mode only, over the full matching folder/media scope | Preserve applied/skipped results and refuse enabling unconfigured/incompatible sources. Do not treat the current source API as an existing bulk media/Kit reassignment command. Any broader explicit native batch action needs its own validated preview and exact affected scope. |
| Folder-routing migration is one-time and idempotent | Preserve the stored report on repeat. Ambiguous folder/Kit/media matches stay disabled and reported; repeat migration must not overwrite authored settings or recatalogue new sources as another cutover. |

Current route names are source evidence, not extra resolvers or an arbitrary workflow editor:

| Media | Scoring route | Editor body route |
| --- | --- | --- |
| News | archived-article-body | archived-article-body |
| Paper | verified-abstract | fulltext |
| Newsletter | feed-issue | feed-issue |
| Podcast | episode-show-notes | transcript |
| Video | reader-description | caption |

Prompt/service/target selection follows [native processing configuration](../specs/native-processing-configuration.md); canonical identity and independent source contexts follow [native source identity](../specs/native-source-identity.md). Imported thresholds/preferences remain migration data, not hard-coded universal new-user defaults. Native configuration must disclose effective scope and side effects using the applicable HIG and existing NNW/AppKit structures.

## Public checks to carry into T04

- Create/reconcile an unconfigured source, rename/move it and replay observations: no AI, hidden rerouting or historical requeue.
- Enable each supported media contract and reject unsupported/mismatched combinations without partial persistence; keep a deliberate cleared contract cleared after reconciliation and restart.
- Change a source while a job runs, disable it before the next spending stage, and explicitly rerun an old item: verify the existing distinct pin/run/manual boundaries rather than a blanket queue snapshot promise.
- Important plus low score, human Nope, absent scoring material and title-only Paper: preserve the actual refusal/authorization and independent Star/read/collection state.
- Apply a bulk mode change to a scope larger than the visible page and containing incompatible entries: exact applied/skipped readback, no media/prompt reassignment or hidden enablement.
- Replay completed folder migration with new/different directory data: retain the previous report and authored settings, while ordinary catalogue reconciliation remains a separate action.

These are required behavior seams for the already scoped feature, not executed tests. Complete acquisition, remote-provider errors and all reconciliation paths were not audited here. T04 implementation remains behind accepted T03 interfaces; no new checkout or implementation owner was started.

Source SHA-256: `backend/feed_settings.py` `524875a0b3f8fdc46495cec25e9f78b9b901ce84f83e9d7a61f4b6f441f762d9`; `backend/pipeline.py` `10a6a7691a1db6f97489f7bcce3d4aff8756369ab99378ba3817edc7870a05a3`; `backend/ingestion.py` `7206a009206c75258e34f8a62a26c96b7325dd65e19150b1527f73c61e7b5042`. Inspected bounded source areas: declarations/schema, contract projection/merge, bulk-save scope, admission pinning, folder-migration entry/idempotency, pipeline Important and live-disabled guards, plus the ingestion pin caller. Hashes identify observed bytes, not a live installation.
