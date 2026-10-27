import Foundation
import RSDatabase
import Synchronization
import Testing

struct DatabaseQueueShutdownTests {
	@Test func rejectedCallbackCompletesWithoutRunningDatabaseBlock() async {
		let queue = DatabaseQueue(databasePath: ":memory:")
		let calls = Mutex((work: 0, rejected: 0))
		queue.runInDatabase(onRejected: {}) { database in
			database.executeStatements("CREATE TABLE fixture (value INTEGER);")
			calls.withLock { $0.work += 1 }
		}
		let closed = await queue.close()
		#expect(closed)
		let accepted = queue.runInDatabase(onRejected: { calls.withLock { $0.rejected += 1 } }) { _ in
			calls.withLock { $0.work += 1 }
		}
		#expect(!accepted)
		let result = calls.withLock { $0 }
		#expect(result.work == 1)
		#expect(result.rejected == 1)
	}
}
