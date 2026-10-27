# IO boot slice provenance

NoNews adaptation: writable startup now accepts an empty database or current schema 41. A populated older/unversioned database and a newer schema are refused before journal/schema changes; their migration requires an independently verified importer. Ordinary current-schema startup also skips empty historical body-table retirement, retaining additional columns, indexes and triggers. The extracted migration functions are not permission to run destructive legacy retirement against imported data.

Reference HEAD `e9ba73f0b44a781ea68c0670114f9281f66f5cd3` (working tree had modifications). The owner authorized reuse. The schema-owner functions and their supporting constants/helpers were extracted from the working tree files identified below. `core.InformationDB` and `jobs.JobQueue` retain only methods used for schema and the public operations; `server.py` adapts the settings-scope jobs and processing-settings dispatch. No CLI, external writer, personal taxonomy or credentials loader is included. The jobs operation adds bounded record framing and continuation; see JOBS-IPC.md. Later tickets own the other operations. `schema.py` refuses unsupported versions before mutation and validates required current tables and columns at startup against an in-memory canonical schema; additional tables and columns are retained.

Source file SHA-256 (working-tree bytes):

- `__init__.py`: `38091c956c9c7a563f4b720d8308f9f06913b65ff841fbcdfd4ddd46b1075dfb`
- `causes.py`: `88d5f400f1f3f61f37d00ff2baacd97ec665e6ef75fa6904be6f4526a8f314fc`
- `content_store.py`: `a710a06702983663612c4297fcea2fed935be7c94ec6392725854c617badad7b`
- `core.py`: `17c00866752ad7fea41b44d5be39703c8553f9b4afcfa3e8a91f2cf28683293e`
- `delivery.py`: `19e3641b5f5c3d77db4a150b6df6c44952336351751342842966e4061e1f6686`
- `feed_settings.py`: `524875a0b3f8fdc46495cec25e9f78b9b901ce84f83e9d7a61f4b6f441f762d9`
- `folders.py`: `6a14c36672db9fd976ecee7cde2d3badc0378d5648187f76f607433b6e8fe974`
- `jobs.py`: `11e0ede95a8379a7ed62f57713f41302b4f2a4744ff17a2e8866a03df16081e1`
- `legacy_content_migration.py`: `29ef2b1658f2b97742a07831b5d94ebc9e9b5b3070c3fdba61c8b33ccd415aad`
- `literature.py`: `7fbdabe89a1a705d77bc5e3887c8dcc1098aaa546b58e99ec2b10fc67daeaaae`
- `literature_mapping.py`: `6700cba041e2133f4566584fa5d405321f6e3845e71244307e2ad2fdce2ae5d0`
- `media_jobs.py`: `3e19cb947805ded4f96d7707e85795723a45248f2841c119e9ee0ccbf1521f98`
- `media_raw_activation.py`: `07bf7878352333bd7767570290dc9f7bbfbd482ca6b570c372f83f21bf655834`
- `media_store.py`: `bd66788473d0e26f47830830f7ae837a8c67661957c2d51241312055e0a591bb`
- `news_media.py`: `540850fd4ed234b1ea8094e728d1d2775cc17410757ee91a871383ce2dfe18cb`
- `pipeline.py`: `10a6a7691a1db6f97489f7bcce3d4aff8756369ab99378ba3817edc7870a05a3`
- `projection.py`: `aed925324aba9174e6feb5794f92b9bdd5c49288a424166cf70557059fd17b30`
- `reading_notes.py`: `25735864eda960e7bfec828ddef3f12ec0c6ea819dc5e1b75e374a3f95b35768`
- `reconciliation.py`: `744e6a18d22a67b68d47aa5204b4945ade580d284e907a3247d36a51d2b039e5`
- `reject_cleanup.py`: `f0719b5562f201d5794a7aec918ae496339da5eeb0e5a4e6dc497635f139c560`
- `reject_media_cleanup.py`: `b1cccc72004b0827d8109299e3cf07496f1ac4383540825d925f995e28b1aefb`
- `schema.py`: `b10584038878bc47d48be0e43530238ad989872bd1f3a16018401609ce2ddcc4`
- `server.py`: `c0ef0cddb50f2caa186d2634c2c630be6d25239b8278159525ed333267bc9647`
- `service.py`: `3a10cce67aeac1181848cbf19cc0c256a1d35a769ede8c2eac5651a424346dec`
- `settings.py`: `b94fd7cda56d61893a631380af8bf105fe42b1dd3c18100267fb956516a3c1b6`
- `zotero.py`: `2caac0f26ed53d5827ea63034e9aa6f96c85697264cf1dead34120a24780cf27`

Fresh schema creation uses a single SQLite transaction with statement-by-statement scripts to avoid implicit commits. Startup probes the actual processing setting inside a rollback-only transaction.

NoNews startup correction: journal-mode conversion retries SQLITE_BUSY within the existing30second bound for concurrent first opens; all failed startup paths close their connection. Canonical in-memory validation closes its reference connection explicitly. The source schema/row preservation and atomic initialization boundaries remain unchanged.

NoNews schema-signature adaptation: backend/schema_semantics.py reuses the reviewed T01 structural-signature algorithm at24675be3f146162aad6c48851780331da8bc2f1e, adding canonical column hidden/generated flags. Startup compares the current database against an independently initialized in-memory schema from the packaged schema owners, before opening writable data. This covers primary/rowid keys, column affinity/default/generation, NOT NULL, unique/partial-index predicates, foreign keys and CHECK contracts; unproved additional restrictive constraints are refused while original structures/bytes are retained. Equivalent renamed indexes and ordinary extra fields/tables remain supported. SQL-expression normalization is conservative; it does not prove arbitrary equivalent custom SQL. No new external package or personal source content is included.

Schema policy correction after R5: canonical-table conflict policies other than SQLite's default ABORT are conservatively refused, including REPLACE/IGNORE/FAIL/ROLLBACK on unique, primary and NOT NULL constraints. Explicit ABORT is accepted. Token scanning excludes quoted strings/comments. The matching snapshot validator is corrected separately in the root; prior T01 acceptance did not cover this shared gap.

NoNews streaming checkpoint: `job_stream.py` is new NoNews code for bounded SQLite TEXT reads and JSON spool writes. The source-derived classifier rules remain in `causes.py`, with a shared streaming classifier; non-aggregate job resolution uses equivalent SQL against the same database snapshot without copying large identifiers into Python. Aggregate-result stage resolution uses a NoNews incremental projection that preserves the source stage/status meaning and duplicate-key behavior without loading unrelated values; original result text remains unchanged.

NoNews deep-aggregate correction: the incremental aggregate projection uses an iterative, spillable one-byte-per-container state stack rather than Python recursion; it retains source status and duplicate-key semantics while allowing deep valid or malformed results to remain readable.
