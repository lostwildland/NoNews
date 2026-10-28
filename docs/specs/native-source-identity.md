# Native source identity and processing-context contract

Implementation contract for T04, with T11/T13/T14/T24/T27 consumers. It refines the accepted parity goal; it is not an implemented bridge or migration result. Source inspected on 2026-10-28 without private accounts, article contents or credentials.

The [feed-policy source audit](../research/io-feed-policy-source-audit.md) supplies the inspected modes, material routes, authored-origin and catalogue/bulk/migration guarantees that this bridge must preserve. Native prompt bindings remain explicit; legacy Kit provenance does not introduce another mandatory inheritance layer.

## Identities that must remain distinct

A native article is an observation of content through a particular account and feed. Its NNW article ID, feed ID and RSS GUID are opaque source identifiers, not global content IDs. Persist a stable installation/library namespace and the original account/feed/article identifiers as a structured binding. Do not construct an ambiguous delimiter-concatenated key, change an NNW identifier, or reuse the old globally unique FreshRSS entry field without namespacing. Preserve imported FreshRSS identifiers as original aliases; do not overwrite them with native IDs.

NNW's independently created account IDs can differ between devices; its special local/iCloud names can also repeat between installations. Consequently a local account binding does not itself identify a shared source on another device. Preserve each observation and map it to the shared content using verified content identity. Source-policy sharing uses an explicit persisted source binding; identical account names or authenticated feed URLs alone do not prove that two account configurations should be linked. Credentials and credential-bearing URLs must not become shared identity payloads or diagnostic labels.

Use the source media-qualified identity contract for DOI, arXiv, supported video identity and normalized URL, retaining raw values and evidence. Do not merge by title, date, summary, model output or body similarity. URL handling must preserve meaningful distinctions and refuse unsupported/ambiguous identifiers; a redirect guess or a parser's broad hostname match is insufficient proof. An unresolved observation remains readable and separately identified, with processing eligibility made explicit. Adding identity evidence cannot silently move existing decisions, materials or receipts to an unrelated item.

Repeated delivery of the same observation is a no-op for identity and automatic admission. Updated RSS bytes may update its observation/material evidence under existing version rules; they do not create a second decision. A known observation returning with a conflicting origin or content identity is a visible conflict, not permission to reparent it. Retain the evidence and require a verified reconciliation path before changing the binding. Removing/readding an account must not reuse another account's old identifier accidentally.

## One decision; independent processing results

The canonical item owns its Yep/Nope history and authorization generation. Each NNW observation keeps its own native read/Star facts. A decision updates all bound presentations without writing NNW read/Star, duplicating a decision event, collecting an external item again or erasing other source observations. Nope invalidates eligible work across contexts through the existing item-level guards; it does not merely hide the currently selected prompt's result.

Processing context is existing product vocabulary, not a new user-authored workflow. A source determines which independently reusable Curator/Editor instructions, execution bindings and policies apply. Different source contexts for the same canonical item must coexist. Identical prompt text does not prove identical configuration; names, stable prompt identities, explicit service/target and independent source-policy history cannot be deduplicated away. Reprocessing creates immutable results with the effective configuration and material references; it never relabels an old result as though it used the current prompt.

Preserve the timing in [native-processing-configuration.md](native-processing-configuration.md): automatic item admission pins the source contract; explicit rerun adopts that source's current compatible contract; processing-run binding freezes prompt versions/models/threshold; a queued explicit Editor target retains its pin. Apply those boundaries within the selected context. A feed edit or second source observation must not overwrite another context's admission pin. A current disabled source policy still prevents automatic spending. Do not create duplicate automatic work merely from observation replay or sync delivery.

Curator, its threshold/reason, Draft and material provenance must be read from a coherent context. Another context's newer result cannot become the displayed result merely because it has the latest timestamp. If a required bound prompt/context is unavailable, show the unavailable state and keep historical results; do not fall back to a different provider or the latest result for the entire item. Verified material bytes may be reused when their identity, role and strategy requirements actually match; sharing a URL alone is insufficient.

## Integrating with the native reader

Bridge at the existing native account/article lifecycle and presentation. Ordinary NNW navigation, subscription membership, search, read/Star and cached articles remain usable when the processor is unavailable. Native receipt of an article does not enable AI, start a historical backfill or require FreshRSS. A new unconfigured source starts disabled under the existing source-setting rule.

Do not invent a News media type or a default prompt just to fit an unconfigured observation into the old typed IO schema. Retain an unresolved observation and its identity durably. T04/T13 must allow a human decision without AI setup; that provisional decision/history must survive later verified media/content resolution. Unresolved observations cannot authorize typed material acquisition or processing. Resolution preserves original aliases and uses the decision-conflict rules; it does not silently discard a prior Nope or duplicate an event when observations converge.

An article opens with the context of its actual source binding. An aggregate timeline row retains that binding; it cannot silently choose the highest score or the latest result from another source. When a retained IO item has multiple contexts but no usable originating native binding, expose their source names and require a choice before processing. Preserve an imported item's historical contract/result as historical context rather than guessing a new source. The reader can still view available content without choosing a processing context. T12/T14 may retain a device-local last explicit display choice; receiving sync never executes it.

Keep one native row for the original article; Curator/Draft/Original are detail layers, not extra articles. Do not introduce extra rows per prompt result. Original NNW timelines may already contain distinct observations of the same content; this contract does not add a global deduplication or ranking feature. In the existing IO canonical-item views, preserve their single-item result semantics. Nope's next-item navigation skips other observations of that same canonical content within the current scope, as [native-decisions.md](native-decisions.md) requires.

Source-specific cards/filters use their selected context's score and threshold. Keep AI qualification distinct from the shared human decision. A score from a different prompt is not a calibrated substitute. Global views must preserve the relevant source/context provenance and the existing filter meaning rather than accidentally evaluating an item against a different source's threshold. Full-result batch preview pins the displayed content/context pairs and does not silently expand one selected item into every context.

## Migration, preservation and sync

Current IO stores only one `item_feed_contracts` row per item and reads a latest successful Curator result at item scope. Those structures alone do not implement NoNews's independent contexts. T04 must add explicit durable context/result associations and non-destructive schema evolution. Preserve legacy rows, version IDs, source pins, timestamps, bindings, unknown fields and original identifiers; retain an unresolved historical association instead of inferring it from a similar prompt name or recent observation. Later migration verification must compare those facts after restart/restore.

Keep IO content and associations independent of NNW cache eviction and account removal. A missing native article is an availability state, not deletion authority for a canonical item or its retained versions. T24 resolves independent client content identities and preserves all original aliases/contexts; it must not sync local SQL row numbers as global IDs. Applying replicated observations, context pins, jobs or receipts performs no model/acquisition/integration work. Execution ownership and conflict handling remain governed by [io-sync-ownership.md](io-sync-ownership.md).

## Required public checks

| Scenario | Required evidence |
| --- | --- |
| Two accounts reuse the same article/feed IDs | Distinct persistent native bindings, correct source policies, no overwritten observation after restart |
| Same verified content in two feeds with different prompts | One canonical decision, both observations and independent results/pins; source A never displays source B's score/Draft |
| Same title, different verified identities; unresolved identity | No accidental merge, retained readable observation and explicit eligibility |
| Repeated delivery, RSS update, conflicting origin | Idempotent admission; correctly versioned changes; conflict retained without silent reparenting or extra spend |
| New source, renamed folder, source-media change | Disabled initial AI; folder/rename does not route processing; old item's media mismatch is a typed refusal |
| Untyped source without AI configured | Reading and human judgment remain available; no invented media/prompt; later verified resolution preserves original decision/history and performs no automatic processing |
| Source edit during a run; explicit rerun; pinned Editor retry | Source-compatible admission/run boundaries, immutable old results and correct job-specific target |
| Nope in one context, then late result from another | One decision event/generation guard; stale writes rejected; unrelated NNW read/Star and completed receipts intact |
| Native list/search while engine unavailable | Existing reading works; retained source identity remains available; no separate web reader or synthetic source rows |
| Imported single-pin history and two-client sync | Original IDs/pins/results retained; missing associations visible; duplicate sync does not execute work or invent another decision |

Tests use the actual managed bridge/read/command boundaries and independent expected identities/results. Later real account/device/migration evidence remains distinct from synthetic client stores. No implementation, source-data import or provider behavior is claimed by this document.

## Source evidence

NNW `Modules/Articles/Sources/Articles/Article.swift` keeps `accountID`, `feedID`, `articleID` and `uniqueID` separately; calculated IDs hash feed ID plus GUID. `AccountManager.createAccount` uses UUIDs except its fixed iCloud identifier; the local account is also separately provisioned. `Account.sendNotificationAbout` and native timeline notifications provide article-update seams; `TimelineCellData` currently contains only original NNW presentation/read/Star fields. These are integration candidates, not a completed API.

IO `core.ingest_observation` first looks up a globally unique FreshRSS entry ID, then uses media-qualified `item_identities`; `feed_settings.pin_item` upserts by item ID; `pipeline._bind_run_contract` resolves the originating feed/pin and `_freeze_run_values` freezes run settings; `core.current_ai` selects the latest successful item-level run. Preserve those source guarantees while extending the explicit context dimension.

Inspected dirty reference checkout HEAD: `e9ba73f0b44a781ea68c0670114f9281f66f5cd3`. SHA-256: `core.py` `17c00866752ad7fea41b44d5be39703c8553f9b4afcfa3e8a91f2cf28683293e`; `feed_settings.py` `524875a0b3f8fdc46495cec25e9f78b9b901ce84f83e9d7a61f4b6f441f762d9`; `ingestion.py` `7206a009206c75258e34f8a62a26c96b7325dd65e19150b1527f73c61e7b5042`; `pipeline.py` `10a6a7691a1db6f97489f7bcce3d4aff8756369ab99378ba3817edc7870a05a3`. No private article or settings contents were read.
