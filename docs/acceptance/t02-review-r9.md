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

1 actionable P2; review incomplete. The reviewer reproduced a 48 MiB traced allocation peak while requesting the first frame of a 16 MiB `result_json`. `server.py` materializes the complete row, JSON string and UTF-8 bytes before checking the 512 MiB limit. Near-limit termination is source-derived, not an observed crash. Preflight field sizes before fetching oversized values and stream encoding to the spool with bounded buffers; preserve complete supported records. A whole-string token yielded by `JSONEncoder.iterencode` would not by itself fix this peak. [Standards review](t3-thread://v1/thread:delegated-task:command%3Amcp%3A5334bca8-6b5e-41fd-84da-2093ead29d99%3Adelegate-task%3Anonews-t02-complete-standards-review-20261028-r9).

The reviewer inspected native lifecycle, IPC, schema validation, major owners and selected tests but left portions of owners, build tooling, tests and context incomplete. This is not an API clearance.

## Spec

No actionable P1/P2 found in inspected portions; review incomplete, not a zero-findings complete verdict. Inspected native lifecycle, private channel, settings/history, all startup schema owners including nested mapping/cleanup owners, selected packaging/tests and the current managed-engine contract. Some connected tests, acceptance/build wiring and remaining specification/review documents were not fully inspected. [Spec review](t3-thread://v1/thread:delegated-task:command%3Amcp%3A5334bca8-6b5e-41fd-84da-2093ead29d99%3Adelegate-task%3Anonews-t02-complete-spec-review-20261028-r9).

The coordinator read both terminal reports and the connected paging/spool path. The original implementation owner must correct memory bounds, test coherent complete large records and controlled capacity refusal, then refresh prepared payload evidence. Subsequent independent review must identify explicit file coverage and fill the unreviewed scope; partial prior reviews cannot clear the API. Later business handlers remain later tickets.

The original owner's R15 continuation reproduced 50,338,513 traced bytes for the 16 MiB first-frame case and left the new 4 MiB-bound regression red. No streaming replacement was implemented, and only the test/evidence files are uncommitted; local and remote HEAD remain the reviewed candidate. This is a reproduction checkpoint, not a correction. Continue the same owner; no external blocker was identified. T30 retains the heavyweight resource.

[The file coverage ledger](t02-review-coverage.json) partitions all 62 pinned changed paths into packaging, native, database and jobs scopes, with original blob identities and separate Standards/Spec status. Each remains pending until explicitly reviewed. This changes review scheduling, not acceptance: every scope and connected seam still needs independent coverage, and changed/new blobs at the final candidate require fresh assessment. No partial prior review is upgraded to a pass.

No code acceptance or integration is claimed. Visible native Ready and appearance remain unobserved; Intel/universal, iOS, CloudKit and release signing remain unverified. T03 can begin only after the API code has passed review and been integrated, with unresolved visual acceptance retained explicitly. T00/T01 remain the only two accepted tickets of 31.
