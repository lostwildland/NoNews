# T30 admission synchronization assessment

Source inspected at `65be895`, including DatabaseQueue, DatabaseWork, FeedSettingsDatabase, SyncDatabase and queued CloudKit send/receive/notification operations. This is a coordinator source assessment, not an independent review or runtime acceptance.

The historical threading guidance in `Technotes/CodingGuidelines.md` requires isolated background parsing and database work to run without locks. The original ticket base already uses `Synchronization.Mutex` for MainThreadOperation cancellation state. These facts do not authorize executing SQL or callbacks while holding a lock.

The coordinator's engineering decision for NoNews is to retain short mutex sections that read/change shutdown admission metadata and atomically enqueue accepted work before closure. Parsing, SQL, queue waits, suspension and application callbacks must execute outside those sections. Rejection callbacks and drained continuations must also run after the lock is released. This preserves the existing serial database ownership and closes the admission/enqueue race without moving business work under a mutex or introducing a dependency cycle.

DatabaseQueue enqueues under its admission mutex and waits afterward; SyncDatabase extracts drain waiters under its mutex and resumes them afterward. DatabaseWork protects only the active bit. These inspected paths fit the decision, subject to the separate transaction-result defect in R17.

**Outstanding correction:** FeedSettingsDatabase `isEmpty` and `allRows` currently call `serialDispatchQueue.sync` and execute SQL inside `closing.withLock`. Move accepted read submission under the gate and completion/wait outside it while preserving ordering against close; releasing the gate before an untracked read would create another close race. Add deterministic coverage of accepted reads, closure and rejection. No blanket Standards exception or complete lock audit is claimed.
