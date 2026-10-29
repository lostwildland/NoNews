# T30 fixture admission review — round 2

Original base: `2782c51bae6f68a91baa6b86c88cc0c5fe5a1cb2`  
Reviewed HEAD: `ca087f58fb53acd94e6ab21ac0e7dd1168ef5806`

This reviews only the fixture-lifetime prerequisite of issue #32. Full T30, migration, sync and UI acceptance remain open.

## Standards

2 actionable P2 findings: previously admitted subscription creation can lose its dependent article update when `startBackground` rejects all work during closing; setting `isDeleted` before draining also discards a queued OPML save, including when busy database closure leaves the directory available for retry. Both violate the documented no-data-loss priority. [Standards review](t3-thread://v1/thread:delegated-task:command%3Amcp%3A5334bca8-6b5e-41fd-84da-2093ead29d99%3Adelegate-task%3Anonews-t30-admission-standards-review-20261028-r2).

## Spec

4 actionable P2 findings. The independent Spec reviewer found the same dependent article-write and OPML-drain defects, plus `Folder.name` accepting changes and notifications during/after closure, and an accepted synchronous `resetAllSelectedForProcessing` submission being discarded by a later untracked task's second admission check. These contradict completing accepted work and refusing later setters without successful notifications. [Spec review](t3-thread://v1/thread:delegated-task:command%3Amcp%3A5334bca8-6b5e-41fd-84da-2093ead29d99%3Adelegate-task%3Anonews-t30-admission-spec-review-20261028-r2).

## Verification and next work

The coordinator re-read both completed reports and the connected Account, LocalAccountDelegate, OPMLFile, Folder, SyncDatabase and DatabaseWork paths at the reviewed HEAD. The four interleavings are supported by those paths but have not yet been reproduced in a new runtime test. Existing 129 focused and 762 full passes do not cover these missing schedules; the prior zero disk-I/O/unlink extraction remains scoped to that candidate.

The same implementation owner must reproduce and fix all four schedules using the existing account-scoped admission/drain mechanism, preserving accepted writes, rejected callbacks, retry, inode checks and fixture ownership. New work is refused; dependent work admitted by an active operation must finish. Queued subscription state must survive even a failed close. Use deterministic behavioral tests, then final-source focused/full native validation and a fresh two-axis review. This candidate is not integrated.

T02 R14 has released the serialized native resource. T30 may use it after rechecking and gracefully stopping only the exact isolated T02 r9 app and child. Root owns shared plans and acceptance; no production profile or reference IO mutation is authorized by this repair.
