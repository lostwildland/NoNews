# T03 implementation evidence

Starting branch `t3/byo-ai-magpie-prompts`, starting SHA `a7136a8c3a08eb161011a3de5fe0cb4903e3bc0b`; accepted T02 integration `e3c6b152214ff4897d5c122c86fed0846c540736` is an ancestor. Issue 5 was read live; it was assigned to lostwildland and had no comments.

The authorized test seams are the native configuration client through authenticated service and durable readback/restart; explicit catalog refresh with synthetic networking; the secure credential-store boundary and failure; prompt save/copy/history/restore and durable synthetic references; and placeholder validation with preserved runtime binding and migration contracts. These seams do not substitute for native UI, real Keychain, or runner acceptance.

## Transport preparation (partial)

The native and stdio frame limits are now 1,310,720 bytes, enough for one 200,000-byte prompt whose bytes each expand to a six-byte JSON escape, plus an envelope. A real stdio service test sends 199,996 control bytes and one four-byte character through an authenticated status request, then reads processing settings on the same process. It failed on the old 64 KiB frame and passed after the change. This is only inbound framing: prompt save/read/copy/history/restore, pagination, oversize configuration refusal and native round trips remain to be implemented and verified. Existing bounded-channel tests passed using a temporary test copy and the system Python as their interpreter; the checkout has no prepared runtime. Native builds and controller checks were not run under the resource restriction.

## Source inspection

Current dirty Information OS source was read without modifying it. SHA-256 of the inspected files: `service.py` 3a10cce67aeac1181848cbf19cc0c256a1d35a769ede8c2eac5651a424346dec; `pipeline.py` 10a6a7691a1db6f97489f7bcce3d4aff8756369ab99378ba3817edc7870a05a3; `magpie.py` 5270d8cdecad006fbfee306018f9d17d63a0f5d7672c1696cc71b3bedf1cc641; `magpie_migration.py` fc634a3628b6d603537bd9d7ba9159c42056c855d8726a59ca0473e499ffcb1d; `ai_client.py` 13c97cd5b8e63842d530e2f526a0632848c4e6ee03c89a089fb101785bd65422. No code was ported from these files in this slice. Their prompt version, one-pass interpolation, directory and drain-first migration contracts still require implementation and public behavioral coverage.

## Durable configuration slice (in progress)

The managed service now stores named service metadata in `app_settings` and prompt text versions in the existing IO `prompt_versions` table, with NoNews-owned prompt metadata in `app_settings`. A transaction commits prompt text and execution binding together; unchanged text reuses the current version. The directory adapter follows the inspected `magpie.py` URL and `GET /v1/models` contract, with a bounded response and explicit bearer authentication for the OpenAI-compatible directory; its implementation is adapted, not a byte-for-byte port. No secret is persisted in service metadata. Copy, text restore, output preference metadata and synthetic source references have public service operations. These are not yet connected to an actual processing runner or a native editor.

System-Python source-fixture tests (`python3 -m unittest ManagedEngine.tests.test_configuration`) passed: a real stdio service saved and read an exact 200,000 UTF-8-byte prompt through restart; oversize edit was refused with prior text/binding and status intact; history/no-op/copy/restore and synthetic reference deletion refusal were exercised; a loopback synthetic directory verified explicit-only refresh, case-sensitive IDs, invalid selection and endpoint invalidation. This is not the declared packaged runtime or native client proof. A source-only `swiftc -frontend -parse` check was permitted by the coordinator; no native controller ran.

The slice is incomplete: directory failure/credential boundary, service and prompt listing, full reference safety, all native forms, runtime placeholder/output binding, legacy Magpie migration actions, and bounded native/public history coverage still need implementation and verification. The current history operation returns metadata in pages, not a full text list; a version is read separately.
