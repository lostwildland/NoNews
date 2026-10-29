# T01 independent review — round 1

Base: `775500c5b007c5917d46f2461544eb4ace8e21ae`
Reviewed HEAD: `7c0f8c76a3f0d6a5252e24794c520aca2e4d07b3`
Both reviewers: independent GPT-6.1 Terra high, read-only. No build, test, UI, private data or remote-service execution by reviewers. The parent independently ran the 26 snapshot tests before review.

## Standards

1 P2: the source connection uses SQLite `mode=ro`, which can still create or modify WAL shared-memory coordination files. This violates the ticket's nonmutating-source requirement. The review was static; add a synthetic test checking source entries and sidecar bytes, and use a WAL-safe boundary that does not open the source directory for SQLite coordination.

Worst within Standards: P2. The original implementation owner is correcting the source-read boundary; no correction or acceptance is claimed yet.

## Spec

2 P1 findings, both against preserving every required asset and rejecting incomplete input:

1. A managed image could exist only remotely after its upload-intent payload was removed. Metadata and expected hashes survived, but independent image bytes did not, while snapshot/restore could succeed. Require preserved verified bytes or refuse this state.
2. An imported draft's database copy could satisfy the version check without its authoritative literature-file mapping. Require the matching owner/file binding or refuse it.

Worst within Spec: P1. These two narrow validation defects were corrected by the coordinator in `1af6f75` on the original implementation branch. Public regression tests first reproduced both missing-asset successes; they now pass for refusal and exact restored local-root/database-payload bytes. The imported-authority refusal also verifies that source authority remains unchanged and that actual database authority can still restore. The existing complete-schema fixture now uses the true synthetic payload hash instead of its old placeholder value. All 28 snapshot tests, compilation and diff checks passed after the corrections.

## Next gate

T01 remains open and unintegrated. Finish the WAL/nonmutating-source correction, retain the asset guards and all existing behavior, then run fresh independent Standards and Spec reviews of the complete original-base-to-final-head diff. Managed-object remote readback, native recovery consumers and full private migration remain later live acceptance work; an absent required asset cannot be waived merely because it is remote.
