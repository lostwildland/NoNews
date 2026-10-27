# IO maintenance and recovery port surfaces

2026-10-28, source-only follow-up to the 41-family inventory and HTTP command audit. This samples implemented maintenance/helper entry points that are not fully described by HTTP routes. It is not an exhaustive script audit, proof that a personal installation uses every script, or NoNews runtime acceptance. No scripts, services, private databases, bodies or credentials were executed/read.

The families below refine existing E2/E3/F7 obligations. They do not require a button for every script or new tickets. Native Settings can hold configured roots/targets; advanced commands expose supported preview, verification and explicit execution. Ordinary reading remains independent of maintenance setup. Replace personal constants with explicit configuration and preserve the same source identity, backup, ownership and conditional-write protections.

| Family | Source implementation evidence | Required retained outcome | Owners |
| --- | --- | --- | --- |
| MAINT-ASSET-PROOF | `scripts/literature_verified_asset_receipt.py`; persisted-asset verifiers in `literature_zotero_note_target.py` and `literature_io_draft_target.py` | Re-read a specific target/receipt and retain exact identities/digests. A per-asset proof is not a write permit, complete-group proof or cleanup authorization. | T21/T22/T27 |
| MAINT-RECONCILE | `scripts/literature_reconcile_stuck_groups.py`, `literature_release_stuck_group.py`; `backend/literature_receipts.py` durable migration operations | Distinguish complete, partial and contradictory interrupted groups. Recheck the bound state and publish the required verification receipt before a permitted release. Contradictory bytes remain held. Releasing a block is not proof of rollback or automatic authorization to rerun. | T20/T21/T22/T27 |
| MAINT-POST-HOC | `scripts/literature_post_hoc_group_receipt.py`, `literature_post_hoc_certify.py` | Preserve separately typed post-hoc evidence and its unverifiable fields. Its source is `post-hoc`, status `assets_verified_post_hoc`, and `apply_complete` stays false. Do not upgrade it to a write-time group receipt during import, display or sync. | T21/T22/T27 |
| MAINT-PRIVATE-RAW | `scripts/register_private_raw_source.py`; `tests/test_register_private_raw_source.py`, `test_private_raw_sources.py` | Preview and verify a specific Raw source/identity, retain the explicit private-file mapping and rollback evidence. No automatic vault cleanup, unrelated tree walking or reassignment of file authority. | T21/T22/T27 |
| MAINT-NOTE-RECONCILE | `scripts/sync_zotero_child_notes.py`, `repair_zotero_bibliography.py` | Preserve prepared child-note IDs, hashes, dates/tags and ownership; imported versions must not replace current IO-authored work. Bibliography repair uses the existing guarded delivery writer, selection/identity checks and serialization, not a second overwrite path. | T16/T17/T22/T27 |
| MAINT-VERIFIED-CLEANUP | `scripts/zotero_verified_cleanup.py`; `tests/test_zotero_verified_cleanup.py` | Keep plan, reviewed plan hash, independent backup verification, per-record outcomes and external readback distinct. Cloud recoverable-trash results do not establish desktop sync or local file removal. No permanent purge, SQLite mutation or broad file movement is supplied by this script. | T16/T21/T22/T27 |

## Evidence levels are part of the behavior

An inspection may read library bytes and write a report to an explicit report destination without changing the library. A receipt may prove only one asset or only facts still observable after an old write. The UI and stored record must state that scope; a green generic `Verified` badge must not imply the operation is complete or executable.

Preserve the original receipt schema/source/status, bound item/version/operation/manifest/batch identities, missing-proof fields and conditional transition requirements. Import and sync retain an unknown newer receipt verbatim with an incompatible/needs-review state. They must not infer completion, synthesize a lost pre-write hash, clear a pending operation, replay a cloud write or authorize cleanup merely because the JSON parsed or hashes agree.

A source recovery script that requires coherent backups, a paused writer, a checked source scope or verified current target bytes keeps those prerequisites in NoNews. Configurability does not turn them into optional preferences. An enabled integration or directory permission is not blanket write authority. Native command preview shows the exact scope and expected action; configuration changes alone perform no maintenance.

Supported external helpers must run against the app-managed installation and explicitly configured targets, not a personal checkout/virtualenv/path. Their actual authenticated command/readback protocol is owned by T17/T18/T22. Do not expose an unauthenticated public API just to preserve an old helper URL. Read-only inspection and configured-target execution are verified separately.

## Historical wrappers and deployment scripts

`scripts/literature_retire_undecided_news_texts.py` explicitly targets legacy `raw_texts` and a FreshRSS body-home transition. It is historical-input compatibility evidence, not an active NoNews default writer. `production_cutover.py`, legacy-content import/restore scripts and host service wrappers likewise contain source-installation assumptions. Preserve their data/authority/recovery outcomes under T27 when their inputs actually exist; do not resurrect retired tables or the manual Markdown editor as normal product features.

Known unsupported historical forms must remain retained and visible until verified migration handles them. Refusing an unsupported original is safer than deleting it, but refusal alone does not satisfy the complete personal-migration goal. The migration owner must account for the actual full source manifest, not assume a clean schema-41 fixture covers these historical cases.

## Public verification cases for the owning tickets

- Reload/restore/sync preserves write-time, post-hoc and per-asset evidence as different records; narrower/unknown proof never authorizes a write or cleanup.
- A complete, partial and contradictory interrupted group produces the respective source disposition. Changing an operation or target bytes after preview causes refusal; release does not automatically rerun it.
- A private Raw registration/rollback retains exact source/target binding and untouched unrelated files; invalid roots, stale identities or missing authority fail visibly.
- Repeated prepared Zotero-note synchronization preserves provenance and current authored draft; changed note set, source hash or parent identity requires renewed verification.
- Cleanup planning and backup verification do not mutate external records. A simulated partial cloud result retains append-only outcomes and pending desktop/local readback; it never claims files were removed.

These tests belong at the actual managed command/helper seams. Existing source tests indicate intent and were not rerun. Real external writes remain limited to explicitly configured authorized test/workflow targets; no personal bulk cleanup is authorized by this audit.

## Source snapshot

Reference checkout is dirty at HEAD `e9ba73f0b44a781ea68c0670114f9281f66f5cd3`; filenames and AST-discovered argument names/docstrings were read without importing modules. Behavioral claims above also use inspected code/contracts, not argument names alone. SHA-256 of representative inspected source:

| Relative source path | SHA-256 |
| --- | --- |
| `scripts/literature_post_hoc_group_receipt.py` | `72bd1daf4a1528b6c428a9b832c95b54d46f1f6df902205867e4685fec32a57f` |
| `scripts/literature_release_stuck_group.py` | `ba0ea211dd4fc2877ed78a19faf3aa0b51efb694e1ad6783c674422ed77ef408` |
| `scripts/register_private_raw_source.py` | `2c821c918a8b81d340dc9167c100d1143704aef1b6f160be42843ca1bdaf1f03` |
| `scripts/sync_zotero_child_notes.py` | `30f69c438f22157c2db1cd6ecaf5584d830dedc4c662064277ed2d1330ce9d2c` |
| `scripts/zotero_verified_cleanup.py` | `142b1fff77fb31325f9068901228e93aca806c54a0d148060816c2dc7c421a63` |
