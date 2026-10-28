# T03 completed receipt identity probe

On 2026-10-28 the coordinator independently reproduced the receipt fast-path defect at committed source `2ee43f01ea187aad232c5d45916e9b11f8760219`.

The probe extracted only `ManagedEngine` from that Git object into a temporary directory and launched its real `stdio_service.py` with system Python, `-B`, and `PYTHONDONTWRITEBYTECODE=1`. It used an authenticated synthetic profile and no provider calls, private data, Keychain, prepared runtime, native app or worker files.

Reproduction:

1. Create a synthetic Magpie service with `PUT /api/config/services` and a fresh mutation ID `M`.
2. Poll `POST /api/config/migration/operation` for `M` until the durable service receipt is complete.
3. Reuse `M` for `PUT /api/settings/processing` with `processors: 2`.
4. Read `GET /api/settings/processing`, close stdin and wait for EOF shutdown.

Expected: the mismatched operation is refused with `invalid_configuration`; same-method/path idempotent retries still return their original receipt.

Observed: step 3 returned the original service receipt as success, without an error code. The processors value remained `1`. EOF shutdown exited `0` and the temporary profile/source were removed. This reproduces the wrong success response; it does not claim a settings write occurred or that the worker correction is verified.

`Application.handle` checks the saved receipt before its existing `_receipt_matches` check in the worker execution path. The original T03 owner received this public-seam result and the requested method/path regression. Fresh corrected-source validation and review remain required.
