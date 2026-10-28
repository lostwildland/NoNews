# T30 provider correction review R25

Fixed BASE `835cda39ad2d9d24946c231dc40d0e6e9ffa9bf7`; HEAD `4850b7cf9027c85d4b16f83b3fde352ddd309ef9`. The single correction commit changes 11 paths, 53 hunks, 203 additions and 46 deletions. The full original-base manifest is 110 paths. Both reviewers inspected all 11 correction paths; this is not a review of the other 99 paths.

## Standards

Three source-derived P2 findings remain:

1. `SyncDatabase.swift:115` reports queue, compensation and fallback failures but leaves no durable retry intent when all three fail after the article status committed. Reporting the failure does not preserve the user change. Couple durable intent to the local change or preserve it before committing, and test the real persistence/retry path.
2. `FeedbinAccountDelegate.swift:1035` and equivalent provider paths can apply a stale response after a newer mark has already been sent and acknowledged. Its pending row is gone, so a gate around the pending read/diff/apply no longer protects it. Retain protection across the fetch interval or discard/refetch stale responses; test fetch → mark → send/ack → apply.
3. `SyncDatabase.swift:199` can reset selected rows outside the status gate while a sender awaits its network acknowledgement. A subsequent successful acknowledgement removes no selected row, allowing replay. Serialize reset/initialization with claim/send/ack or complete initialization before any send.

## Spec

The first finding is P1 on the Spec axis: R24 requires a durable retryable intent or the prior local state. When both are lost, repeating an identical mark can yield no changed IDs and cannot rebuild the outbox. Some callers discard the returned error. Add an end-to-end real article/sync database failure and retry regression.

The stale fetch finding is Spec P2. Merely re-reading pending IDs inside the gate does not protect a mark whose sender already acknowledged and removed its row. Preserve local mutation/acknowledgement identity across the fetch interval without holding the reconciliation gate over network fetches.

## Coverage and evidence

Changed hunks and added tests read in all 11 paths: CloudKit, Feedbin, Feedly, NewsBlur and ReaderAPI delegates; NewsBlur internal reconciliation; Account fixture tests; SyncDatabase implementation, error type and status-table tests; worker acceptance note. Connected tracing includes article persistence and callers, provider send/ack, initialization/reset, gates, reconciliation and account admission/drain. Full cancellation, every provider callback and the other 99 manifest paths remain outside this bounded verdict.

The successful fallback does notify/schedule, gate release is awaited on success and error, and NewsBlur uses changed IDs. These fixes do not clear the three failure schedules above. No reviewer ran tests/builds, GUI, live providers, CloudKit or private data.

The coordinator independently read 149/0/0 in `20-14-35` and 150/0/0 in `20-20-17`; the latter's test tree contains 10 passing SyncStatusTable tests. Neither summary has a runtime warning. These are result readbacks, not independent reruns or proof of private test-source equality. Final full build/iOS/live sync and T30 acceptance remain open.
