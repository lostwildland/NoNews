# IO command-to-ticket coverage

2026-10-28 source audit. This supplements the 41 capability families with every `/api/` string or regex fragment in the current `Application.handle` dispatch. The 54 fragments include guard prefixes, aliases and a refused legacy surface; they are not 54 independent user features. Each fragment has one primary family below. All corresponding NoNews implementations remain subject to their ticket tests and runtime acceptance.

Source: `backend/server.py`, working-tree SHA-256 `c0ef0cddb50f2caa186d2634c2c630be6d25239b8278159525ed333267bc9647`. The IO checkout is dirty; its Git HEAD alone cannot identify these bytes. Only source code and existing capability/ticket documents were read. No services, private bodies, databases or credentials were accessed.

The source paths are traceability labels. NoNews may expose the same behavior through its private authenticated command boundary and native controls; this catalog does not require a public HTTP server, a FreshRSS settings page or literal legacy route compatibility.

| Source fragments and first line | Capability and native destination | Owning tickets | Source status / constraints |
| --- | --- | --- | --- |
| `/api/health` :357 | Engine liveness and configured/actual workers | T02, T20 | Implemented |
| `/api/settings/integrations/check` :372<br>`/api/settings/integrations` :375 | Integration status and explicit connection checks | T16, T17, T18, T19, T28 | Implemented; status is separate from successful external work |
| `/api/settings/magpie/migration` :380 | Magpie pending-target migration preview, pause and apply | T03, T27 | Implemented maintenance; historical provenance must remain |
| `/api/settings/providers` :394 | Retired provider-management prefix | T03 | Explicitly refused in IO; no inherited working feature |
| `/api/settings/magpie` :396 | Magpie endpoint and read-only target directory | T03 | Implemented |
| `/api/reader/` :414<br>`/api/items/` :415<br>`/api/jobs/` :608 | Read-scope and retry-permission routing fragments | T02, T20 | Guard fragments, not independent endpoints |
| `/api/review` :424<br>`/api/review/counts` :427<br>`/api/entries` :435 | Review/entry lists and counts | T04, T12, T14, T20 | Implemented; list windows are not global totals |
| `/api/review/batch/preview` :429<br>`/api/backlog/preview` :431 | Full-result batch preview | T15 | Implemented aliases |
| `/api/items/([A-Za-z0-9_-]+)` :440 | Canonical item detail and current facts | T04, T12, T13 | Implemented |
| `/api/feeds` :445 | Sources and per-source statistics | T04, T23 | Implemented |
| `/api/failures` :447<br>`/api/activity` :456<br>`/api/queue` :540<br>`/api/jobs` :569<br>`/api/deliveries` :628 | Failures, activity, queue, jobs and deliveries | T20 | Implemented |
| `/api/literature/progress` :458<br>`/api/literature/receipts` :460 | Literature progress and receipt evidence | T18, T20, T22 | Implemented |
| `/api/literature/reading-notes` :465 | Personal reading-copy status, create and explicit recreate | T17 | Implemented; no empty note and no implicit overwrite |
| `/api/literature/adoption` :480<br>`/api/literature/adoption/` :484<br>`/api/literature/adoption/intents` :529 | Adoption begin/finalize/reconcile/status and intent listing | T18 | Implemented dispatcher prefixes plus listing; uncertain intents retain protection |
| `/api/backlog` :533<br>`/api/backlog/process` :535 | Backlog scope and full-result process commands | T15, T22 | Implemented; rejects obsolete rescore payload |
| `/api/queue/stop` :567 | Stop queued work | T20 | Implemented; does not imply running work was killed |
| `/api/projection/retry` :616<br>`/api/failures/retry` :619<br>`/api/failures/dismiss` :624 | Projection retry, same-cause failure retry and dismiss | T04, T20 | Implemented |
| `/api/deliveries/zotero/([A-Za-z0-9_-]+)/retry` :631<br>`/api/deliveries/newsletter/([A-Za-z0-9_-]+)/retry` :635 | Zotero and issue-delivery retry | T16, T18, T20 | Implemented |
| `/api/items/([A-Za-z0-9_-]+)/process` :639 | Stage-specific processing and model-free note maintenance | T05, T06, T07, T08, T09, T10, T11, T17, T19, T23 | Implemented; preserve manual-ReEdit material authorization and pinned target |
| `/api/jobs/([A-Za-z0-9_-]+)/retry` :658 | Guarded job retry | T20 | Implemented |
| `/api/filter-views` :666 | Quick-view list/save/delete | T14 | Implemented |
| `/api/settings/feeds` :673 | Feed policies and bulk updates | T04 | Implemented |
| `/api/settings/processing` :708 | Worker-count settings | T02, T20 | Implemented |
| `/api/settings/kits` :719 | Kit create/copy/rename/delete and threshold changes | T03, T04, T27 | Implemented capability becomes independent prompt configurations plus source policy; retain legacy IDs/history |
| `/api/settings/(models\|prompts\|integrations)` :743 | Prompt text/history/restore and bound model settings | T03 | Models/prompts implemented; integration mutations explicitly not ready in this branch |
| `/api/review/([A-Za-z0-9_-]+)/publish-plan` :755 | Issue adoption plan and chosen-version preview | T18 | Implemented |
| `/api/review/([A-Za-z0-9_-]+)/actions` :770 | Select/Reject, read actions, compatibility Star actions and adoption | T04, T13, T16, T18 | Implemented commands; legacy Star alias must not redefine NNW Star |
| `/api/review/batch` :824<br>`/api/commands/([A-Za-z0-9_-]+)/undo` :873 | Batch accept-AI/Reject and command undo | T13, T15 | Implemented; preserve pinned membership/results and undo deadlines |
| `/api/reader/items/([A-Za-z0-9_-]+)` :879<br>`/api/reader/item` :882 | Native reader material/state projection by item or source entry | T04, T12 | Implemented |
| `/api/items/([A-Za-z0-9_-]+)/raw-assets` :887 | Owned Raw-image asset reads | T19 | Implemented trust boundary |
| `/api/items/([A-Za-z0-9_-]+)/cleanup-request` :890 | Cleanup facts and explicit guarded execution | T21 | Implemented; no bypass of deadlines, references or backup |
| `/api/items/([A-Za-z0-9_-]+)/drafts/([A-Za-z0-9_-]+)` :902<br>`/api/items/([A-Za-z0-9_-]+)/(raw\|drafts)/([A-Za-z0-9_-]+)` :905 | Protected draft deletion and immutable Raw/draft version reads | T11, T12, T21 | Implemented |
| `/api/signals` :908<br>`/api/reconcile` :908 | Source reconciliation signals | T04, T20 | Implemented aliases; source read/Star signals never become human decisions |

## Important subcommands and exclusions

- Adoption has distinct begin, finalize, status and reconcile operations. A missing or empty external spool is not proof of no usage; uncertain writes keep their cleanup hold. T18 must retain the durable registration/readback flow.
- Manual ReEdit of pending paper material retains its explicit confirmation and Raw/body fingerprint. This is different from ordinary automatic eligibility or editing text inside the reader. The old reader manual Markdown editor remains retired.
- Current source allows deletion of eligible draft versions but protects adopted versions. The control acts on the version actually being viewed, including compare mode. T11/T21 must retain that distinction.
- Magpie target migration maps pending work/configuration, preserves historical snapshots and versions, and requires a fresh directory before applying choices. T03/T27 own this maintenance function alongside ordinary connection editing.
- Direct/BYO services are an authorized new NoNews capability. The old IO provider-management prefix currently refuses requests; copying that dead surface is not an implementation of the new capability.
- Integration status/check operations exist, while the generic integration-setting mutation branch explicitly refuses unimplemented mutations. Configurable integration forms are a required NoNews product adaptation, not an inherited source success.

## Coverage boundary

Every extracted dispatch fragment is classified above and mapped to existing tickets. This audit found no need for a new top-level capability family; it makes existing batch, history, adoption and maintenance obligations explicit. It does not prove runtime behavior, exhaust all helper/CLI entry points, or establish current production configuration. T16/T17/T18/T22 must still inspect their active helper scripts and adapt personal bootstrap/retired-schema coupling rather than copying it. Final T30 reconciles these source operations with the capability matrix and actual NoNews evidence.
