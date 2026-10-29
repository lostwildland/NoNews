# T01 independent review — round 3

Base: `775500c5b007c5917d46f2461544eb4ace8e21ae`
Reviewed HEAD: `5014a503bf2769cd50c4c988f73fd7686795bd27`
Independent GPT-6.1 Terra high reviewers; static, read-only review without builds, tests, UI, production data or remote service access.

## Standards

1 P2: `literature_assets.archive_path` may contain a SQLite BLOB despite its TEXT declaration. The compression test calls `endswith` before the common reference validator, causing a TypeError/CLI traceback instead of a controlled refusal. This violates the no-crashes priority. Worst within Standards: P2.

The coordinator reproduced the public CLI failure using a full-schema fixture and guarded the compression test by text type, letting the common validator reject malformed values. Commit `63bf1e8` preserves the source database and refuses publication without a traceback. Follow-up `1efbce9` normalizes evidence whitespace; the original-base diff check then passed. All 42 focused tests passed after the fix.

## Spec

1 P2: table/column names alone do not establish the required schema safety invariants. Removing the unique partial `media_document_one_pending` index still passes snapshot/verify and produces a restored database without that invariant, contrary to rejecting incomplete input. Validate the required semantic indexes and constraints against the canonical current schema, allowing extra objects and reordered columns. Add public snapshot and verify regressions. Worst within Spec: P2.

The canonical 71-table/592-column gate and prior remote-byte, imported-Draft/Raw and WAL corrections are present. The larger semantic-schema correction remains with the original T01 owner; no test bypass or source repair is accepted.

## Verification and disposition

The parent reran 42 tests with ResourceWarning treated as errors and Python compilation. Source originals and production data were not used. T01 remains open and unintegrated pending the semantic-schema correction and fresh independent review of its final HEAD against the original base. Quiescent writers remain required; fixture success is not personal-cutover acceptance.
