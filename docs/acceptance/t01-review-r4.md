# T01 independent review — round 4

Base: `775500c5b007c5917d46f2461544eb4ace8e21ae`
Reviewed HEAD: `4e561e8ededddc91e3bea75e4a78dd28d6adb905`
Independent GPT-6.1 Terra high reviewers; static original-base review without tests, builds, UI, production data or remote calls.

## Standards

1 P2, worst P2: a SQLite BLOB in literature_cleanup_backups.path reaches Path before input validation. Snapshot can emit an uncaught TypeError rather than a controlled refusal. This violates the no-crashes priority. Validate text first, with a public CLI source-preservation/no-publication regression.

## Spec

1 P2, worst P2: the gate checks primary-key names but not SQLite rowid aliasing. Replacing raw_snapshots.id INTEGER PRIMARY KEY with TEXT PRIMARY KEY preserves the compared constraints, yet breaks subsequent IO inserts that omit id and use lastrowid. Record/validate the required alias and test snapshot and verify refusal, as the ticket requires rejection of incomplete/tampered input.

Prior managed-byte, imported-authority, WAL staging and semantic safety guards remain present on static inspection. Reviewer results do not establish production completeness.

## Coordinator corrections and verification

Public regressions reproduced the backup BLOB traceback and admission of TEXT/DESC key alterations. A shared asset-path validator now handles backup construction and normal binding; non-text document input receives an explicit safe refusal. The descriptor records 19 rowid aliases and the gate compares them, accounting for separate PK indexes in DESC and WITHOUT ROWID cases. A public restore check creates Raw snapshots afterward and verifies generated IDs via lastrowid.

The initial full run failed the descriptor guard because of an old generated module cache, despite matching on-disk hashes. After removing that cache, a synthetic duplicate source hash correctly hit the existing unique constraint; the fixture was corrected to use distinct hashes. The final focused suite passed 45 tests; compilation and original-base diff checks passed before commit. No test, constraint or validation gate was weakened. Detailed sequence and descriptor hash are in the ticket evidence.

T01 remains open and unintegrated pending fresh two-axis review of the corrected HEAD against the original base. No personal cutover, remote-byte readback or native migration UI was exercised.
