import Darwin
import Foundation
import SQLite3
import Testing
import RSWeb
import SyncDatabase
@testable import Account

@Suite(.isolatedWebserviceResponses) @MainActor struct AccountFixtureLifetimeTests {
	private enum FixtureError: Error, Equatable { case expected }

	@Test func throwingBodyStillRemovesItsFixture() async throws {
		let manager = TestAccountManager()
		var path = ""
		await #expect(throws: FixtureError.expected) {
			try await manager.withAccount(type: .feedbin) { account in
				path = account.dataFolder
				throw FixtureError.expected
			}
		}
		#expect(!path.isEmpty)
		#expect(!FileManager.default.fileExists(atPath: path))
	}

	@Test func removalClosesTheOriginalDatabaseFiles() async throws {
		let manager = TestAccountManager()
		let account = manager.createAccount(type: .feedbin)
		let identities = try ["DB.sqlite3", "Sync.sqlite3", "FeedSettings.db"].map {
			try identity(account.dataFolder + "/" + $0)
		}
		for file in identities { #expect(hasOpenFile(file)) }
		try await manager.deleteAccount(account)
		for file in identities { #expect(!hasOpenFile(file)) }
	}

	@Test func closesDatabasesBeforeRemovingOnlyOwnedDirectory() async throws {
		TestingURLProtocol.setResponse("tags.json", file: "JSON/tags_add.json")
		TestingURLProtocol.setResponse("subscriptions.json", file: "JSON/subscriptions_initial.json")
		let manager = TestAccountManager()
		try await manager.withAccount(type: .feedbin) { other in
			let otherPath = other.dataFolder
			let foreignManager = TestAccountManager()
			await #expect(throws: (any Error).self) {
				try await foreignManager.deleteAccount(other)
			}
			#expect(FileManager.default.fileExists(atPath: otherPath))
			var removedPath = ""
			try await manager.withAccount(type: .feedbin) { account in
				removedPath = account.dataFolder
				try await account.refreshAll()
				let feed = try #require(account.idToFeedDictionary["1296379"])
				feed.editedName = "Lifetime fixture"
				let sync = try #require(account.delegate as? FeedbinAccountDelegate).syncDatabase
				await sync.insertStatuses([SyncStatus(articleID: "fixture", key: .starred, flag: true)])
				#expect(try await sync.selectPendingStarredStatusArticleIDs().contains("fixture"))
				let files = ["DB.sqlite3", "Sync.sqlite3", "FeedSettings.db"].map { account.dataFolder + "/" + $0 }
				for file in files { #expect(isOpen(file)) }
				let closed = await account.closeForFixtureRemoval()
				#expect(closed)
				#expect(FileManager.default.fileExists(atPath: account.dataFolder))
				for file in files { #expect(!isOpen(file)) }
				#expect(try stringValue(in: files[2], sql: "SELECT editedName FROM feedSettings WHERE feedID = '1296379'") == "Lifetime fixture")
				#expect(try stringValue(in: files[1], sql: "SELECT articleID FROM syncStatus WHERE articleID = 'fixture'") == "fixture")
			}
			#expect(!FileManager.default.fileExists(atPath: removedPath))
			#expect(FileManager.default.fileExists(atPath: otherPath))
		}
	}

	private func isOpen(_ path: String) -> Bool {
		let expected = URL(fileURLWithPath: path).resolvingSymlinksInPath().path
		for descriptor in 0..<getdtablesize() {
			var buffer = [CChar](repeating: 0, count: Int(MAXPATHLEN))
			if fcntl(descriptor, F_GETPATH, &buffer) == 0 {
				let name = String(decoding: buffer.prefix { $0 != 0 }.map { UInt8(bitPattern: $0) }, as: UTF8.self)
				if URL(fileURLWithPath: name).resolvingSymlinksInPath().path == expected {
					return true
				}
			}
		}
		return false
	}

	private func identity(_ path: String) throws -> (dev_t, ino_t) {
		var info = stat()
		guard lstat(path, &info) == 0 else { throw CocoaError(.fileReadNoSuchFile) }
		return (info.st_dev, info.st_ino)
	}

	private func hasOpenFile(_ identity: (dev_t, ino_t)) -> Bool {
		for descriptor in 0..<getdtablesize() {
			var info = stat()
			if fstat(descriptor, &info) == 0 && info.st_dev == identity.0 && info.st_ino == identity.1 {
				return true
			}
		}
		return false
	}

	private func stringValue(in path: String, sql: String) throws -> String? {
		var database: OpaquePointer?
		guard sqlite3_open_v2(path, &database, SQLITE_OPEN_READONLY, nil) == SQLITE_OK else {
			throw CocoaError(.fileReadUnknown)
		}
		defer { sqlite3_close(database) }
		var statement: OpaquePointer?
		guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
			throw CocoaError(.fileReadUnknown)
		}
		defer { sqlite3_finalize(statement) }
		guard sqlite3_step(statement) == SQLITE_ROW, let value = sqlite3_column_text(statement, 0) else { return nil }
		return String(cString: value)
	}
}
