# T30 cancellation consumer review R13

Base `2782c51bae6f68a91baa6b86c88cc0c5fe5a1cb2`; pin `e46b1b4d03b55204f2c379c26444266168c9776d`. Both reviewers inspected all 22 consumer changed-hunk sets and verified their ledger blobs and original-base diff/whitespace. Connected reads covered the status utility/command and undo, both timeline operations and callers, smart-feed/account aggregation, scripting, Spotlight and widget publication. The axes ran in separate fresh tasks within the available concurrency slots.

## Standards

One source-derived P2: `ArticleUtilities.markArticleIDs` ignores errors and always completes; `MarkStatusCommand` registers undo and calls `didMark` regardless of success. The iOS caller removes the complete captured selection, including failed accounts in a partial write. New cancellation makes the unchanged helper wrong. Propagate per-account outcomes and constrain success UI and undo/redo to actual successes; consider scripting status setters too. No separate material smell was established.

## Spec

Three source-derived P2 findings:

- The same status utility/command chain projects failed or partial writes as complete success.
- iOS clears the timeline before a fetch that can reject; the operation's failure finishes its queue entry but omits the caller's result callback. Preserve the previous presentation and distinguish failure from a successful empty result, completing current callbacks exactly once.
- Widget encoding deletes old icons before fetching replacement data. If fetching rejects, the published JSON remains while its icon files may have been removed. Publish only a complete replacement, defer cleanup until the atomic write succeeds and protect the files referenced by the published snapshot.

No reviewer ran tests, GUI or integration actions. Root checked the connected source and sent the findings to the original implementation owner. Status-helper/command and timeline signatures need a coherent caller migration, so this is an implementation batch, not a one-line `try?` removal. Foundation undo registration timing must remain valid; moving redo registration after an asynchronous wait without handling UndoManager state is not a complete fix. Do not erase unrelated history or publish partial data as a complete fetch. These fixes and their public regressions remain pending.

The coordinator independently read the completed native result for source `5013c9128e619003c635c2e941a9c1cc31e85099`: 791 passed, zero failures/skips. Its action log has 1,206 emitted outputs / 10,697 lines and zero disk-I/O or vnode-unlink matches. That run was already in flight before R13 findings; it proves neither the future consumer changes nor CloudKit callback ownership. No new normal build is claimed. Final full/build verification is deferred until known source findings stabilize; focused batches continue first.
