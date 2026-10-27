# T02 packaged candidate — round 9 review preparation

Original base: `c9ecfa14e884a7ce8895bb13eec3ea8711cbef90`  
Candidate HEAD: `d21a38dd8e9822746c5ccc6b85a74e71a03d56d2`  
Artifact code HEAD: `897f43c47f83f29efb2b240cb1373ad822c6d70c`

The sole later commit changes `docs/acceptance/t02-managed-engine.md`. The original-base diff is nonempty and passes whitespace checking. Local and remote candidate refs match and the implementation worktree is clean.

## Packaged evidence

The original owner reports a successful normal acceptance build, four sandboxed relocated-payload behavioral tests, three paging and five startup tests. The complete source suite remains 20 passed with one optional reference comparison skipped; the earlier 753-test macOS run applies to `b95cffa`, before later Python-only corrections. No later full native run is implied.

The coordinator independently checked the relocated `/tmp/nonews-t02-r9-installed/NetNewsWire.app`: isolated identity and deep strict signature verification pass. Embedded `server.py`, `schema.py`, jobs contract and prepared manifest match current source/stage. The executable hash is `b4b53ad3ef62f5eaeb6a73a15fdbc7cff4cdbed1b924fc6f7f27a19d6ebcf9a0`; manifest hash is `91b1c9c1b7252ba4c8e4a0a91d51b0f50e776972d816d1950d26ba894c658024`. One initial coordinator lookup used the wrong resource-directory spelling; the actual `Contents/Resources/ProcessingEngine/PAYLOAD-MANIFEST.json` exists and matches.

At this readback the exact app PID 74950 owns bundled interpreter PID 74956. This proves process relationship, not visible Settings Ready. The owner released the heavyweight native resource to T30; the app may be gracefully stopped for its tests.

## Standards

Pending fresh complete independent review of the pinned original-base change, including first-party schema-owner code and connected tests. The incomplete R8 assessment is not a clean pass.

## Spec

Pending fresh independent review against issue #4 and the managed-engine/full-parity contracts. Later business handlers remain later tickets; the current foundation must satisfy its actual lifecycle, storage and IPC requirements.

No code acceptance or integration is claimed. Visible native Ready and appearance remain unobserved; Intel/universal, iOS, CloudKit and release signing remain unverified. T03 can begin only after the API code has passed review and been integrated, with unresolved visual acceptance retained explicitly. T00/T01 remain the only two accepted tickets of 31.
