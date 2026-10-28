# T03 configuration service review R1

Base `a7136a8c3a08eb161011a3de5fe0cb4903e3bc0b`; pin `4075a7d85870d89872e179aa277050ccbef8b850`. Both reviewers completely inspected seven assigned paths: `configuration.py`, `magpie_migration.py`, `server.py`, `stdio_service.py`, `payload_sources.py`, and both configuration/migration test files. Both verified the pinned objects, original-base diff/log and whitespace; connected reads covered schema/transactions, native credential/binding callers and relevant reference IO source contracts. All findings below are source-derived, not reviewer reproductions.

## Standards

Four findings; worst P1:

- P1: migration's effective-Kit selection accepts an empty-media live feed contract and misses source mismatch refusal, potentially rewriting a pending checkpoint with the wrong target.
- P2: explicit provider/model mapping loses to a saved target, while the reported basis claims the explicit choice was used.
- P2: rendering treats every caller-provided key as a valid placeholder, without the applicable role/media restrictions.
- P2: unbounded migration reports can exceed transport capacity after apply commits and resumes claims, hiding the actual result.

No separate material smell was asserted.

## Spec

Four findings; worst P1:

- P1: oversized preview/evidence/apply output needs pagination and a small durable acknowledgement; the caller must learn that a mutation committed.
- P1: migration retains service association only in evidence. Deletion checks prompts alone, allowing removal of the gateway still required by live migrated configuration/work.
- P2: sufficiently oversized input framing terminates the engine instead of refusing configuration while keeping unrelated operations usable.
- P2: frozen legacy history persists a SQLite rowid boundary, which can change during compaction. Stable IDs/membership must preserve the exact imported history and current text.

Both axes remain changes-requested; they are not whole-T03/API acceptance. The original implementation owner has the full findings and is continuing source/public-service fixes. Native preferences, real Keychain failures, declared-runtime/package, UI and later runner integration remain separate gates.

The coordinator independently ran `python3 -B -W error::ResourceWarning -m unittest ManagedEngine.tests.test_configuration ManagedEngine.tests.test_configuration_migration -v` at the clean pin: four tests passed in 7.268 seconds. These exercised actual stdio with synthetic SQLite/loopback directories under system Python, including exact 200,000-byte readback/history/restore and restart/migration. They do not cover the findings above, actual credentials, packaged runtime or native UI. No production source/configuration was changed or executed.
