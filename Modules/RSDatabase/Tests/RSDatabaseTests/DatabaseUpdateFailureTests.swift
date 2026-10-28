import Foundation
import Testing
import SQLite3
import RSDatabase
import RSDatabaseObjC

struct DatabaseUpdateFailureTests {
	@Test func failedCommitRollsBackAndPreservesItsError() throws {
		let database = try #require(FMDatabase(path: ":memory:"))
		try #require(database.open())
		defer { _ = database.close() }
		try #require(database.executeStatements("PRAGMA foreign_keys=ON; CREATE TABLE parent (id INTEGER PRIMARY KEY); CREATE TABLE child (id INTEGER REFERENCES parent(id) DEFERRABLE INITIALLY DEFERRED); INSERT INTO parent VALUES (1); INSERT INTO child VALUES (1);"))
		let result = database.executeUpdateInTransactionResult("DELETE FROM parent WHERE id=1")
		if case .failure(let error) = result {
			#expect(error.code == Int(SQLITE_CONSTRAINT))
		} else { Issue.record("Deferred COMMIT failure reported success") }
		let rows = try #require(database.executeQuery("SELECT id FROM parent", withArgumentsIn: []))
		#expect(rows.next() && rows.int(forColumnIndex: 0) == 1)
		rows.close()
		try #require(database.executeUpdate("DELETE FROM child", withArgumentsIn: []))
		#expect(database.executeUpdateInTransaction("DELETE FROM parent WHERE id=1"))
	}

	@Test func failedBeginDoesNotExecuteUpdateOrCommitCallerTransaction() throws {
		let database = try #require(FMDatabase(path: ":memory:"))
		try #require(database.open())
		defer { _ = database.close() }
		try #require(database.executeStatements("CREATE TABLE fixture (id INTEGER PRIMARY KEY); INSERT INTO fixture VALUES (1);"))
		try #require(database.beginTransaction())
		try #require(database.executeUpdate("INSERT INTO fixture VALUES (2)", withArgumentsIn: []))
		#expect(!database.executeUpdateInTransaction("DELETE FROM fixture"))
		let rows = try #require(database.executeQuery("SELECT count(*) FROM fixture", withArgumentsIn: []))
		#expect(rows.next() && rows.int(forColumnIndex: 0) == 2)
		rows.close()
		#expect(database.rollback())
	}

	@Test func batchInsertPreservesFirstFailureAndStops() throws {
		let database = try #require(FMDatabase(path: ":memory:"))
		try #require(database.open())
		defer { _ = database.close() }
		try #require(database.executeStatements("CREATE TABLE fixture (value INTEGER CHECK(value > 0));"))
		#expect(!database.insertRows([["value": -1], ["value": 2]], insertType: .normal, tableName: "fixture"))
		#expect(database.lastErrorCode() == SQLITE_CONSTRAINT)
		let rows = try #require(database.executeQuery("SELECT count(*) FROM fixture", withArgumentsIn: []))
		#expect(rows.next() && rows.int(forColumnIndex: 0) == 0)
		rows.close()
	}
}
