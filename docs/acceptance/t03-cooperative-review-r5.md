# T03 cooperative configuration review R5

Correction base `6da5efa249ede069bf8ebccec8ecb86d198da9e2`; reviewed head `00c2665dbe49f4cc0fbf4a2d85e744ae38c94030`. Both independent reviewers checked all seven scoped blobs, ancestry, single-commit log, 245-addition/11-deletion diff and whitespace. They read every assigned changed-hunk set and connected transaction, snapshot, framing, polling and native caller seams. No reviewer ran tests. The 318-line preferences-controller delta and full 21-path original-base coverage remain excluded.

## Standards axis

No independent documented Standards violation or material Fowler smell was reported. The Standards reviewer separately raised three **Spec P2** findings: delivered errors retain queue capacity, queued-write commit outcomes can be lost on expiry/stop, and queued rendering loses its final wire budget. These are not a whole-ticket Standards clearance.

## Spec axis

Four source-derived findings, none runtime-reproduced by the reviewer:

- **P1 — queued saves can commit after reported failure.** Shutdown exempts queued mutations from cancellation and waits for their threads while the native controller fails callbacks. Expiry can also remove their eventual results. Without a durable receipt or reliable reconciliation, the user can receive unavailable/expired even though the save later commits. Preserve the contract's observable saved state and prior configuration on definitive failed saves. The Standards reviewer reports this concern as Spec P2; each severity is retained.
- **P2 — failed operations exhaust the queue.** Failed completions are not marked read, so the next-operation reclamation ignores them. Thirty-two failures/cancellations within the idle window block subsequent operations. Reclaim acknowledged errors without losing appropriate retries.
- **P2 — queued rendering loses response budget.** Queue capture omits the supplied budget and result polling adds another envelope. Near-limit output can become generic response-too-large instead of the distinct render refusal. Account for the actual final escaped envelope without imposing a smaller product limit.
- **P2 — completed preview cancellation retains its unread snapshot.** The cancellation returns expired without releasing the published result whose identity the client never receives. Synchronize cancellation/publication/cleanup and keep owned resources reachable until released.

## Coordinator correction and remaining work

Root corrected only the acknowledged-error finding in pushed `dd58d6eed26dab5a0f496fcca9ebe9db01c5a02d`. The final authenticated stdio regression reproduces `migration_busy` against extracted exact00c2665; green verifies 40 errors, repeated reads, status and a subsequent settings write. That regression and the full greater-than16MiB cooperative case passed together: two tests in14.057seconds under system Python with ResourceWarning as error. Cleanup closes the service before removing its temporary data directory. Source compilation and whitespace passed; no native/deadline or prepared-payload proof was added. Fresh independent re-check remains required.

The same original owner delivered partialf96d605 with reported render-envelope and unread-preview cleanup changes and three migration passes. The queued-save P1 remains open. R14 now focuses on transaction-coupled outcome receipts and native recovery; root additionally identified a cancelled-preview error branch that bypasses error acknowledgement and needs lifecycle verification. These reported P2 fixes are not independently cleared. After T30's release, T03 has a conditional strict standalone native/component grant once the P1 source and functional tests are ready. Root did not replace the owner or weaken support to reject all writes during migration. Actual controller wiring, strict Swift6 harness, EOF/expiry concurrency, exact payload integrity, app/Keychain/HIG and runner acceptance remain open.
