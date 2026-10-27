# T01 snapshot investigation (incomplete)

- Ticket: #3, T01: Lossless IO snapshot, manifest and independent restore.
- NoNews baseline: `775500c5b007c5917d46f2461544eb4ace8e21ae`.
- Read-only Information OS source HEAD: `e9ba73f0b44a781ea68c0670114f9281f66f5cd3`; the checkout was dirty, so this SHA alone does not identify its working-tree contents.
- Status: **not implemented or accepted**. No snapshot, verify, or restore interface has been delivered; no production data was opened.

## Source evidence and coverage limits

`backend/schema.py` declares schema version 41 in `schema_meta`, and delegates DDL to many owners. Version 41 alone does not describe all historical tables: schema setup conditionally retires old body tables. Preserve unknown tables and their contents rather than assuming an exhaustive list.

`backend/content_store.py` stores body and draft versions and their text in separate tables. A version marked `imported` is a verified copy, but the corresponding literature file remains authoritative. `backend/legacy_content_migration.py` records mapping and verification evidence; it distinguishes missing, changed, unclaimed, and unverifiable files. Treating an imported copy as the file's replacement would change authority.

`backend/literature_mapping.py` defines `literature_files`, `literature_raws`, and `literature_drafts`, including relative paths, identity and file hashes. `backend/service.py` also resolves Raw through private-source records and archived artifacts, with distinct roots. `backend/media_store.py` records remote objects, upload-intent payloads and local pending staging paths. The source investigation has not established a complete, safe mapping of all these forms and roots into a portable snapshot, nor whether each historical reference represents required live data, a tombstone, or an external projection. Unmapped legacy forms and remote objects must be explicitly accounted for, not silently omitted.

The schema owners also include processing jobs, pipeline runs, settings, deliveries, media intents and receipts. A complete backup must retain their bytes and relationships, including unfamiliar tables; counting selected rows is insufficient. Database and file snapshots also need a defined consistency boundary when files change while a live SQLite backup runs.

## Remaining work and verification

Implement public snapshot/verify/restore operations with SQLite online backup, complete asset-reference accounting, safe handling of untrusted paths, manifests and symlinks, and fail-closed, interruption-safe destination publication. Build synthetic fixtures using the actual schema and verify the independently restored database and assets against independent expectations, including WAL, corruption, changed files, existing destinations and repeated/interrupted attempts. Reports must contain no private content or secrets. No tests or native build were run in this investigation. This evidence does not establish T01 acceptance or authorize production migration.
