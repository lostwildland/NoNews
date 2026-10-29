# T01 independent review — round 6

Base: `775500c5b007c5917d46f2461544eb4ace8e21ae`
Reviewed HEAD: `7580501f88a5cb9b21fcff96fd8ddd9a2168a9d3`
Corrected HEAD: `24675be3f146162aad6c48851780331da8bc2f1e` (pushed and remote hash confirmed)
Independent GPT-6.1 Terra high reviewers reproduced their findings using synthetic public inputs. Neither axis claims full-suite, production, native UI or remote verification.

## Standards

1 P2, worst P2: unbounded JSON decoding/traversal raises RecursionError on deeply nested metadata instead of cleanly refusing. The public CLI reproduction used an unknown table with 1100-level metadata_json. Bound input depth and translate parser/traversal depth failures into SnapshotError.

## Spec

2 findings, worst P1. P1: HTML image inventory stops after its first usable URL attribute; a remote data-viewer-src hides a required missing local src. Public snapshot/verify/restore can therefore succeed without the local bytes. Inventory all independently loadable attributes or refuse ambiguity.

P2: extra restrictive schema constraints are accepted; CHECK(starred=1) admits a snapshot but blocks the current IO item insert relying on DEFAULT0. Refuse unsupported constraints while retaining harmless additions.

## Coordinator corrections and verification

Untrusted JSON decoding now converts invalid/deep input into SnapshotError, with an iterative 128-container-depth check before recursive reference traversal. Public CLI tests cover snapshot and verify at depths200/1100, unchanged source, no traceback and no publication.

The schema gate rejects extra CHECK/foreign-key/unique/not-null constraints that cannot be proved safe, canonical-table triggers, expression indexes and nonunique partial indexes. Required columns preserve the absence as well as presence of defaults. Ordinary additional nullable columns, plain indexes and unknown table/BLOB rows still round-trip. Some equivalent custom schema additions are conservatively refused; originals remain untouched. Public refusal regressions cover seven additional-constraint families.

All usable HTML URL attributes are inventoried. Newly discovered secondary attributes are appended after the legacy inventory, keeping original image indices stable for reviewed aliases. The new alias-index regression first failed after the image coverage fix, then passed with stable indices; restored original-alias and secondary-image bytes remain accessible after the vault is moved. Existing direct-file precedence and owner/hash validation remain.

Final focused suite:50tests passed with ResourceWarning as errors. Python compilation and original-base diff checks passed. Source/schema descriptors were not weakened and source IO was not modified. T01 remains open and unintegrated pending fresh review. Real personal migration, live remote readback and downstream recovery-consumer integration are not accepted by these synthetic checks.
