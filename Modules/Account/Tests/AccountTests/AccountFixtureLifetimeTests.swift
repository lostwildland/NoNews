import Darwin
import Foundation
import SQLite3
import Testing
import RSWeb
import SyncDatabase
import Articles
import Synchronization
import RSCore
@testable import Account

@Suite(.isolatedWebserviceResponses) @MainActor struct AccountFixtureLifetimeTests {
	private enum FixtureError: Error, Equatable { case expected }
	private final class NotificationCounter: Sendable { let count = Mutex(0) }

	@Test func retainedModelsCompleteRenameAfterAccountIsReleased() async throws {
		let manager = TestAccountManager()
		var account: Account? = manager.createAccount(type: .onMyMac)
		let feed = try #require(account?.createFeed(with: "Original", url: "https://example.com/released", feedID: "released", homePageURL: nil))
		let folder = try #require(account?.ensureFolder(with: "Original"))
		try await manager.deleteAccount(try #require(account))
		account = nil
		#expect(feed.account == nil)
		#expect(folder.account == nil)
		let feedResult: Result<Void, Error> = await withCheckedContinuation { continuation in
			feed.rename(to: "Rejected") { continuation.resume(returning: $0) }
		}
		let folderResult: Result<Void, Error> = await withCheckedContinuation { continuation in
			folder.rename(to: "Rejected") { continuation.resume(returning: $0) }
		}
		if case .failure(let error) = feedResult { #expect(error is CancellationError) } else { Issue.record("Feed rename unexpectedly succeeded") }
		if case .failure(let error) = folderResult { #expect(error is CancellationError) } else { Issue.record("Folder rename unexpectedly succeeded") }
	}

	@Test func admissionStopsDuringCloseWhileAcceptedWorkFinishes() async throws {
		let manager = TestAccountManager()
		let account = manager.createAccount(type: .onMyMac)
		let feed = account.createFeed(with: "Original", url: "https://example.com/during", feedID: "during", homePageURL: nil)
		let path = account.dataFolder
		let (started, startSignal) = AsyncStream<Void>.makeStream()
		let (release, releaseSignal) = AsyncStream<Void>.makeStream()
		let (closing, closingSignal) = AsyncStream<Void>.makeStream()
		account.onFixtureClosingForTesting = { closingSignal.yield(()) }
		account.startBackground {
			feed.editedName = "Before"
			startSignal.yield(())
			for await _ in release { break }
			feed.editedName = "Admitted"
			let changed = await account.database.markAndFetchNewAsync(articleIDs: ["admitted"], statusKey: .starred, flag: true)
			#expect(changed == ["admitted"])
		}
		for await _ in started { break }
		let close = Task { await account.closeForFixtureRemoval() }
		for await _ in closing { break }
		let notifications = NotificationCounter()
		let observer = NotificationCenter.default.addObserver(forName: .feedSettingDidChange, object: feed, queue: nil) { _ in
			notifications.count.withLock { $0 += 1 }
		}
		let displayObserver = NotificationCenter.default.addObserver(forName: .DisplayNameDidChange, object: feed, queue: nil) { _ in
			notifications.count.withLock { $0 += 1 }
		}
		feed.editedName = "Rejected"
		#expect(feed.editedName == "Before")
		#expect(notifications.count.withLock { $0 } == 0)
		NotificationCenter.default.removeObserver(observer)
		NotificationCenter.default.removeObserver(displayObserver)
		#expect(await account.fetchArticlesAsync(.feed(feed)).isEmpty)
		let rejected = await account.database.markAndFetchNewAsync(articleIDs: ["rejected"], statusKey: .starred, flag: true)
		#expect(rejected.isEmpty)
		let created = await account.database.createStatusesIfNeededAsync(articleIDs: ["rejected"])
		let deleted = await account.database.deleteAsync(articleIDs: ["admitted"])
		#expect(!created && !deleted)
		#expect(FileManager.default.fileExists(atPath: path))
		releaseSignal.yield(())
		let closed = await close.value
		#expect(closed)
		#expect(feed.editedName == "Admitted")
		#expect(try stringValue(in: path + "/FeedSettings.db", sql: "SELECT editedName FROM feedSettings WHERE feedID = 'during'") == "Admitted")
		#expect(try stringValue(in: path + "/DB.sqlite3", sql: "SELECT starred FROM statuses WHERE articleID = 'admitted'") == "1")
		#expect(try stringValue(in: path + "/DB.sqlite3", sql: "SELECT starred FROM statuses WHERE articleID = 'rejected'") == nil)
		try await manager.deleteAccount(account)
		#expect(!FileManager.default.fileExists(atPath: path))
	}

	@Test func failedAccountCloseCanBeRetried() async throws {
		let manager = TestAccountManager()
		let account = manager.createAccount(type: .feedbin)
		let path = account.dataFolder
		let feed = account.createFeed(with: "Original", url: "https://example.com/fixture", feedID: "fixture-feed", homePageURL: nil)
		feed.editedName = "Accepted"
		let sync = try #require(account.delegate as? FeedbinAccountDelegate).syncDatabase
		let settingsIdentity = try identity(path + "/FeedSettings.db")
		var destination: OpaquePointer?
		guard sqlite3_open(":memory:", &destination) == SQLITE_OK else { throw CocoaError(.fileWriteUnknown) }
		defer { sqlite3_close(destination) }
		let backup = try #require(account.feedSettingsDatabaseForTesting.withDatabaseForTesting { database in
			guard let source = database.sqliteHandle() else { return nil as OpaquePointer? }
			return sqlite3_backup_init(destination, "main", OpaquePointer(source), "main")
		})
		async let first = account.closeForFixtureRemoval()
		async let second = account.closeForFixtureRemoval()
		let results = await (first, second)
		#expect(!results.0 && !results.1)
		#expect(FileManager.default.fileExists(atPath: path))
		#expect(hasOpenFile(settingsIdentity))
		feed.editedName = "Rejected"
		#expect(feed.editedName == "Accepted")
		let settingsWrite = account.feedSettingsDatabaseForTesting.setString("Rejected", for: feed.url, column: .editedName)
		#expect(!settingsWrite)
		#expect(await account.fetchArticlesAsync(.feed(feed)).isEmpty)
		await #expect(throws: CancellationError.self) {
			try await sync.selectPendingCount()
		}
		let inserted = await sync.insertStatuses([SyncStatus(articleID: "rejected", key: .starred, flag: true)])
		#expect(!inserted)
		#expect(try stringValue(in: path + "/FeedSettings.db", sql: "SELECT editedName FROM feedSettings WHERE feedID = 'fixture-feed'") == "Accepted")
		let finishResult = sqlite3_backup_finish(backup)
		#expect(finishResult == SQLITE_OK)
		try await manager.deleteAccount(account)
		#expect(!FileManager.default.fileExists(atPath: path))
		#expect(!hasOpenFile(settingsIdentity))
	}

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

	@Test func retainedFeedRejectsChangesAfterClose() async throws {
		let manager = TestAccountManager()
		try await manager.withAccount(type: .onMyMac) { account in
			let feed = account.createFeed(with: "Original", url: "https://example.com/feed", feedID: "fixture", homePageURL: nil)
			let files = try ["DB.sqlite3", "FeedSettings.db"].map { try identity(account.dataFolder + "/" + $0) }
			feed.editedName = "Before close"
			let closed = await account.closeForFixtureRemoval()
			#expect(closed)
			feed.editedName = "After close"
			#expect(feed.editedName == "Before close")
			let articles = await account.fetchArticlesAsync(.feed(feed))
			#expect(articles.isEmpty)
			for file in files { #expect(!hasOpenFile(file)) }
			#expect(try stringValue(in: account.dataFolder + "/FeedSettings.db", sql: "SELECT editedName FROM feedSettings WHERE feedID = 'fixture'") == "Before close")
		}
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
