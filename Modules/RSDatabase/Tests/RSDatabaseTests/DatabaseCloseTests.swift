import Testing
import SQLite3
import RSDatabaseObjC

struct DatabaseCloseTests {
	@Test func busyCloseKeepsConnectionForRetry() throws {
		let source = try #require(FMDatabase(path: ":memory:"))
		let destination = try #require(FMDatabase(path: ":memory:"))
		let sourceOpened = source.open()
		let destinationOpened = destination.open()
		try #require(sourceOpened && destinationOpened)
		let sourceHandle = try #require(source.sqliteHandle())
		let destinationHandle = try #require(destination.sqliteHandle())
		let backup = try #require(sqlite3_backup_init(OpaquePointer(destinationHandle), "main", OpaquePointer(sourceHandle), "main"))
		let closedWhileBusy = source.close()
		let retainedHandle = source.sqliteHandle()
		let finished = sqlite3_backup_finish(backup)
		let closedAfterFinish = source.close()
		let destinationClosed = destination.close()
		#expect(!closedWhileBusy)
		#expect(retainedHandle != nil)
		#expect(finished == SQLITE_OK)
		#expect(closedAfterFinish)
		#expect(destinationClosed)
	}
}
