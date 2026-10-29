# T01 independent review — round 2

Base: `775500c5b007c5917d46f2461544eb4ace8e21ae`
Reviewed HEAD: `fcb211463ad3f93e57178287e1647fa6ee70cb50`
Independent GPT-6.1 Terra high reviewers, read-only; no builds, tests, UI, production data or remote calls by reviewers.

## Standards

1 P2: gzip decompression can raise `zlib.error` for a valid header with corrupt DEFLATE; catching only OSError/EOFError lets the public command emit a traceback. Catch and translate this as invalid input, with a public regression. The previous source-SHM mutation was addressed in static inspection; runtime correctness was not independently exercised by the reviewer.

Worst within Standards: P2. Coordinator correction in `f5e5c15` reproduced the exception first, then converted it to SnapshotError and tested a clean CLI refusal without traceback.

## Spec

2 P1 findings against complete required-state preservation and rejection of incomplete input:

1. A schema-41 version marker is accepted even when canonical IO tables/columns are missing. Existing abbreviated positive fixtures demonstrate that this is allowed. Require the current structure while retaining additional unknown tables/columns.
2. An imported Raw version can pass with an archive-path binding instead of its authoritative literature Raw mapping. Require the actual owner/file mapping or refuse the state.

Worst within Spec: P1. The coordinator reproduced and fixed the narrow imported-Raw guard in `f5e5c15`. The larger schema gate and canonical fixture adaptation remain with the original implementation owner. No test-only bypass, broad exception assertion, deleted coverage or truncated fixture may substitute for that gate.

## Verification and disposition

After the two narrow corrections, the parent ran 37 snapshot tests with ResourceWarning errors enabled, compilation and diff checks successfully. These retain WAL/source-byte, managed-object, draft-authority, image, recovery and interruption checks. They do not resolve the incomplete-schema finding: the positive fixtures must still be made canonical.

T01 remains open and unintegrated. Its next independent review must use the original base and final implementation HEAD after required-schema validation and fixture adaptation. No private cutover or remote-byte readback has been performed.
