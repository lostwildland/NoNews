# NoNews settings and configuration parity catalog

2026-10-27. Product implementation contract derived from current IO source and the user's ten decisions. Values below are source defaults or explicit design decisions, not readings of the owner's private configuration. Imported values always take precedence over defaults. This catalog supplements tickets; it is not acceptance evidence.

## Native settings organization

Current NNW Settings uses native toolbar categories General, Accounts and Advanced. Retain that vocabulary and framework. Add a coherent Processing category for services/prompts/source policy and an Integrations category for external tools; place storage/migration/sync and maintenance groups in the appropriate existing/native category rather than introducing a top-level toolbar item for every backend module. Source Inspector links to that source's policy; ordinary reading does not require navigating settings.

A complex category may use native list-detail forms and disclosure sections. Primary fields describe the task; Advanced exposes expert knobs and diagnostics. The underlying function remains available even when its expert details are collapsed. No independently styled FreshRSS settings page or web dashboard is transplanted into native chrome.

## Configuration ownership and defaults

| Group / field | Scope | Existing contract / migration behavior | Native presentation and owning ticket |
| --- | --- | --- | --- |
| NNW General and reading appearance | app/device | Existing NNW values preserved | Existing General; T00/T29 |
| Timeline swipe actions | device interaction | New NNW-first install retains Read/Star; optional Decisions mapping is right Yep/left Nope; IO migration defaults to its existing decision gestures and preserves any actually saved input preference | General > Article actions; equivalent menu/buttons remain, see native-decisions.md; T13/T27 |
| Accounts, credentials and subscriptions | account | Existing account semantics; local accounts still differ from cloud services | Existing Accounts and Keychain; T00/T25 |
| AI service name/endpoint | service | Source Magpie URL preserved; BYO direct service additional supported path | Processing > Services; T03 |
| Authentication | service/device security | Secure reference; never plain synced settings or prompt export | Native secure fields/Keychain; T03/T25 |
| Target/model directory | service | Read-only refresh, no inference; stale/unavailable target distinct from valid configuration | Target picker with actual connection status; T03 |
| Prompt name and role | reusable prompt | Split each legacy Kit role without losing identity/references | Processing > Prompts, Curator/Editor grouping; T03 |
| Prompt content | versioned prompt | Saved database prompt remains execution authority; no hidden file or other-prompt fallback | Editor with declared input/output help; T03 |
| Title language and generated-text typography | reusable prompt/run | New prompts follow instructions/preserve generated text; imported configurations retain applicable Chinese-title/editorial formatting requirements. Historical keys/results are immutable | Prompt editor > Advanced; [output contract](native-output-preferences.md); T03/T06/T11/T27 |
| Prompt model/target | prompt | Explicit bound connection/target; requested vs actual model retained | Same prompt editor; T03 |
| Prompt history and restore | prompt text | Restore older text as a new current text version, retaining visible current execution binding; identical text is a no-op; prior runs keep old versions | Version list and Restore Text; T03 |
| Supported input placeholders | role/material | Existing supported names preserved, including legacy description alias; invalid placeholders fail before sending | Discoverable variable help/insert controls and validation; T03/T11 |
| Prompt references, copy and removal | prompt | Shared change shows affected sources; delete cannot leave silent broken references | Usage list, copy, replace/unbind choice; T03 |
| Processing mode | feed | New/unconfigured feed disabled; Normal/Important retain current distinction | Source Inspector / Processing > Sources; T04 |
| Media type | feed | Explicit news/paper/newsletter/podcast/video, no silent auto change | Source type picker with required material description; T04 |
| Curator and Editor selection | feed | Independent prompt selections; legacy pair can map to two entries without forcing a new Kit UI | Two prompt pickers; T04 |
| Selection threshold | feed | 0–10; source's effective legacy Kit threshold copied exactly. Old seed values (News 7/Paper 9/others 7) are not replacements for saved values | Threshold with short automation consequence; T04 |
| Automatic processing/Editor advancement | feed | Preserve current mode/threshold behavior, explicit scope; edits do not reprocess history | Clear source policy control; T04/T11 |
| Scoring material policy | feed/media | One currently supported strategy per type; material identity/completeness invariant | Readable effective policy; expert options only when a real supported choice exists; T04–T10 |
| Body/transcript/caption policy | feed/media | Separate scoring input vs full body; no ASR/download invention | Source material policy and actionable unavailable states; T04–T10 |
| Folder and batch source edits | chosen feeds | Folder membership is navigation/bulk scope, never implicit routing | Multi-select preview/explicit field changes; T04 |
| Existing subscription state | source | Subscribed/missing/unverified are observations, not processing switches | Inspector status, preserve historical rows; T04 |
| Worker concurrency | app/processor host | Source default 4, valid range 1–8; source launch override/imported setting preserved | Processing > Advanced, finishes held work when shrinking; T20 |
| HTTP-first domains | acquisition | Preserve source domain preference overrides; do not force a personal allowlist on new users | Advanced acquisition routes; T05 |
| Browser/manual timeouts | acquisition | Source defaults 90/120 seconds, values positive; imported override preserved | Advanced acquisition controls; T05 |
| Per-host concurrency | acquisition | Source default 1; overrides do not bypass job/data safety | Advanced acquisition controls; T05/T20 |
| Browser and OCR component availability | device | Managed installed runtime; missing optional component reported honestly | Component status/setup, optional expert overrides; T02/T05/T07 |
| Manual material access/retry | item/job | Existing retry/manual-required distinctions | In-context action and Activity, not hidden settings; T05–T10/T20 |
| Classification vocabularies | media/profile | Preserve current Paper constraints/News categories as migrated values; user-editable valid taxonomy | Advanced source/processing taxonomy editor; T23 |
| Zotero endpoint/library/collection | integration | Preserve exact owner destination via private migration; remove hardcoded account/collection constants | Integrations > Zotero with verified target; T16 |
| Zotero credential | integration security | Central secure reference, not ordinary settings export | Keychain connection; T16 |
| Yep-to-collection linkage | integration/policy | Retain owner's existing explicit-intent behavior; optional visible configuration for others | Clear action consequence control; T13/T16 |
| Obsidian vault and personal copy destination | integration | Preserve mappings and security-scoped access; export remains explicit and protects edits | Integrations > Obsidian; T17 |
| Existing helper/CLI/Linter integration | integration/device | Existing working workflow kept, unsupported/missing dependency visible | Connection detail and advanced helper setup; T17/T18 |
| Issue paths/naming/eligible frontmatter | adoption profile | Existing issue selection/date/state rules preserved; no automatic new issue | Integrations > Adoption, target preview; T18 |
| Receipt/spool mappings and reconciliation | integration | Preserve source freshness/provenance; an empty spool is not proof of unused material | Advanced connection/Activity; T18 |
| Media upload destination/namespace | integration | Preserve optional upload intent/staging/receipts and public/private boundary | Integrations > Media, explicit enable/target; T19 |
| Nope cleanup policy | storage | Existing owner's behavior preserved; expose policy instead of changing semantics under new wording | Advanced > Storage, meaningful effect summary; T13/T21 |
| Recovery duration | storage | Existing source recovery is 7 days. Configurable duration must keep imported pending cleanup deadlines unless an explicit replan occurs | Duration and affected-item preview; T21 |
| Protected references and late-write revocation | invariant | Cannot turn off to simplify personal preferences | Status explanation, not a disable switch; T13/T21 |
| Body/draft/file authority | invariant/migration | Preserve current per-asset authority until verified cutover; user copy never becomes automatic authority | Detail/storage provenance and migration report; T01/T21/T27 |
| Quick views | reading preferences | Existing grouped filter document, save/apply/delete; maximum/name rules inherited | Native filter popover, current chips; T14 |
| Date/search/sort | current reading scope | Existing IO/FreshRSS behavior; don't silently add it to saved views if source format doesn't store it | Native list controls; T14 |
| History catalog/source/time scope | maintenance profile | Existing explicit scope and discovery/import behavior retained; coverage unknowns stay visible | Advanced > Library Maintenance; T22 |
| Sync choice/status/conflicts | app/account/data | New IO data needs explicit supported channel; NNW read/star unaffected | Native sync Settings/status; T24/T25/T26 |
| Migration source/snapshot/mapping | one-time workflow | All data/assets accounted for, preview/restore/rollback, no historical inference/write replay | Native import flow and redacted local evidence; T01/T27 |

## Required legacy Kit transition

Preserve the original Kit records and IDs for historical evidence. For each active Kit, expose independently selectable Curator and Editor prompt configurations, with explicit targets and all prompt versions. Populate each feed's new threshold from its effective legacy threshold, including a feed/contract/run's pinned history where relevant. A model switch or restore does not rewrite old results. Duplicate roles can initially remain separate named entries; do not deduplicate solely by similar text and accidentally combine different bindings.

A migration report must show missing/ambiguous assignments and preserve their source rows. If a prompt/target is missing, keep that feed visibly incomplete/disabled rather than substituting a generic prompt or another provider. Importing history does not schedule processing.

## Actions are not settings

ReCurate, ReEdit, compare drafts, accept AI decisions, batch process, retry, cancel, collect, adopt, export and restore are explicit commands with scope and side effects. A preference can configure their defaults, but a saved toggle must not silently execute history or turn a remote write into a mere preference save. Validation, correct identity, material completeness, anti-overwrite, authorized targets and trustworthy receipts remain mandatory.

## Verification boundary

This catalog comes from source definitions, not the owner's saved values or real-service checks. Each implementation owner verifies corresponding fields/actions via the public API and native surface; final migration verifies actual private values locally without publishing them. Any newly found runtime option with user-visible capability is added here and to the owning ticket.
