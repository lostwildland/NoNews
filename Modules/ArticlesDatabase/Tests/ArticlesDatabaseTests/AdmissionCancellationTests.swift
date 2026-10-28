import Foundation
import Testing
import RSDatabase
import Articles
@testable import ArticlesDatabase

@MainActor @Suite struct AdmissionCancellationTests {
	@Test func deferredConstraintRejectsCommitAndConnectionRemainsUsable() async {
		let queue = DatabaseQueue(databasePath: ":memory:")
		let table = ArticlesTable(name: "articles", accountID: "commit-fixture", queue: queue, retentionStyle: .feedBased)
		queue.runInDatabaseSync { database in
			#expect(database.executeStatements("PRAGMA foreign_keys=ON; CREATE TABLE articles (articleID TEXT PRIMARY KEY); CREATE TABLE child (articleID TEXT REFERENCES articles(articleID) DEFERRABLE INITIALLY DEFERRED); INSERT INTO articles VALUES ('stored'); INSERT INTO child VALUES ('stored');"))
		}
		let succeeded = await withCheckedContinuation { continuation in
			table.delete(articleIDs: ["stored"]) { continuation.resume(returning: $0) }
		}
		#expect(!succeeded)
		queue.runInDatabaseSync { database in
			let result = database.executeQuery("SELECT count(*) FROM articles WHERE articleID='stored'", withArgumentsIn: [])
			#expect(result?.next() == true && result?.int(forColumnIndex: 0) == 1)
			result?.close()
			#expect(database.executeStatements("DELETE FROM child;"))
		}
		let retry = await withCheckedContinuation { continuation in
			table.delete(articleIDs: ["stored"]) { continuation.resume(returning: $0) }
		}
		#expect(retry)
		#expect(await queue.close())
	}
	@Test func failedArticleDeleteIsNotReportedAsSuccess() async {
		let queue = DatabaseQueue(databasePath: ":memory:")
		let table = ArticlesTable(name: "articles", accountID: "delete-fixture", queue: queue, retentionStyle: .feedBased)
		queue.runInDatabaseSync { database in
			#expect(database.executeStatements("CREATE TABLE articles (articleID TEXT); INSERT INTO articles VALUES ('stored');"))
		}
		let success = await withCheckedContinuation { continuation in
			table.delete(articleIDs: ["stored"]) { continuation.resume(returning: $0) }
		}
		#expect(success)
		queue.runInDatabaseSync { database in
			#expect(database.executeStatements("DROP TABLE articles;"))
		}
		let failure = await withCheckedContinuation { continuation in
			table.delete(articleIDs: ["stored"]) { continuation.resume(returning: $0) }
		}
		#expect(!failure)
		#expect(await queue.close())
	}
	@Test func failedStatusQueryIsNotASuccessfulEmptyRead() async {
		let queue = DatabaseQueue(databasePath: ":memory:")
		let table = StatusesTable(queue: queue)
		queue.runInDatabaseSync { database in
			#expect(database.executeStatements("CREATE TABLE statuses (articleID TEXT, read INTEGER, starred INTEGER);"))
		}
		for (key, value) in [(ArticleStatus.Key.read, false), (.starred, true)] {
			let result: Result<Set<String>, Error> = await withCheckedContinuation { continuation in
				table.fetchArticleIDsAsync(key, value) { continuation.resume(returning: $0) }
			}
			if case .success(let ids) = result { #expect(ids.isEmpty) }
			else { Issue.record("A valid empty status query failed") }
		}
		queue.runInDatabaseSync { database in
			#expect(database.executeStatements("DROP TABLE statuses;"))
		}
		for (key, value) in [(ArticleStatus.Key.read, false), (.starred, true)] {
			let result: Result<Set<String>, Error> = await withCheckedContinuation { continuation in
				table.fetchArticleIDsAsync(key, value) { continuation.resume(returning: $0) }
			}
			if case .failure(let error) = result {
				#expect(!(error is CancellationError))
				#expect((error as NSError).domain == "FMDatabase")
				#expect((error as NSError).code == 1)
			} else { Issue.record("A failed status query returned successful empty IDs") }
		}
		#expect(await queue.close())
	}

	@Test func emptyCountsSucceedButClosedDatabaseRejects() async throws {
		let database = ArticlesDatabase(databaseFilePath: ":memory:", accountID: "counts-fixture", retentionStyle: .feedBased)
		let empty = try await database.fetchArticleCountsAsync(feedIDs: [])
		#expect(empty.totalCount == 0 && empty.statusesCount == 0)
		#expect(try await database.fetchLastUpdateDates().isEmpty)
		try await database.createStatusesIfNeededAsync(articleIDs: ["stored"])
		let populated = try await database.fetchArticleCountsAsync(feedIDs: [])
		#expect(populated.statusesCount == 1)
		database.beginClosing()
		await #expect(throws: CancellationError.self) {
			_ = try await database.fetchArticleCountsAsync(feedIDs: [])
		}
		await #expect(throws: CancellationError.self) {
			_ = try await database.fetchLastUpdateDates()
		}
		#expect(await database.close())
	}

	@Test func failedStatusCreationRollsBackAndCanRetry() async throws {
		let database = ArticlesDatabase(databaseFilePath: ":memory:", accountID: "creation-fixture", retentionStyle: .feedBased)
		#expect(database.executeSQLForTesting("PRAGMA foreign_keys=ON; CREATE TABLE fixture_parent (id INTEGER PRIMARY KEY); CREATE TABLE fixture_child (id INTEGER REFERENCES fixture_parent(id) DEFERRABLE INITIALLY DEFERRED); CREATE TRIGGER fixture_status AFTER INSERT ON statuses BEGIN INSERT INTO fixture_child VALUES (1); END;"))
		await #expect(throws: (any Error).self) { try await database.createStatusesIfNeededAsync(articleIDs: ["stored"]) }
		#expect((try await database.fetchArticleCountsAsync(feedIDs: [])).statusesCount == 0)
		#expect(database.executeSQLForTesting("DROP TRIGGER fixture_status; DROP TABLE fixture_child; DROP TABLE fixture_parent;"))
		try await database.createStatusesIfNeededAsync(articleIDs: ["stored"])
		#expect((try await database.fetchArticleCountsAsync(feedIDs: [])).statusesCount == 1)
		#expect(await database.close())
	}

	@Test func closedQueueCompletesCountCallbackWithCancellationOnce() async {
		let queue = DatabaseQueue(databasePath: ":memory:")
		let table = ArticlesTable(name: "articles", accountID: "queue-fixture", queue: queue, retentionStyle: .feedBased)
		#expect(await queue.close())
		let result: Result<ArticleCounts, Error> = await withCheckedContinuation { continuation in
			table.fetchArticleCountsAsync([]) { continuation.resume(returning: $0) }
		}
		if case .failure(let error) = result { #expect(error is CancellationError) }
		else { Issue.record("Closed queue returned a successful count") }
		let dates: Result<[String: Date], Error> = await withCheckedContinuation { continuation in
			table.fetchLastUpdateDatesAsync { continuation.resume(returning: $0) }
		}
		if case .failure(let error) = dates { #expect(error is CancellationError) }
		else { Issue.record("Closed queue returned successful dates") }
	}

	@Test func unchangedStatusIsSuccessfulButClosedWriteIsCancelled() async throws {
		let database = ArticlesDatabase(databaseFilePath: ":memory:", accountID: "status-fixture", retentionStyle: .feedBased)
		try await database.createStatusesIfNeededAsync(articleIDs: ["stored"])
		let unchanged = try await database.markAsync(articleIDs: ["stored"], statusKey: .read, flag: true)
		#expect(unchanged.isEmpty)
		database.beginClosing()
		await #expect(throws: CancellationError.self) {
			_ = try await database.markAsync(articleIDs: ["stored"], statusKey: .read, flag: false)
		}
		#expect(await database.close())
	}

	@Test func closedQueueCompletesStatusCallbackWithCancellationOnce() async {
		let queue = DatabaseQueue(databasePath: ":memory:")
		let table = ArticlesTable(name: "articles", accountID: "queue-status-fixture", queue: queue, retentionStyle: .feedBased)
		#expect(await queue.close())
		let result: Result<Set<String>, Error> = await withCheckedContinuation { continuation in
			table.mark(["stored"], .read, true) { continuation.resume(returning: $0) }
		}
		if case .failure(let error) = result { #expect(error is CancellationError) }
		else { Issue.record("Closed queue returned a successful status write") }
	}
	@Test func emptyReadsSucceedAndClosedReadsCancel() async throws {
		let database = ArticlesDatabase(databaseFilePath: ":memory:", accountID: "read-fixture", retentionStyle: .feedBased)
		#expect(try await database.fetchArticlesAsync(feedID: "feed").isEmpty)
		#expect(try await database.fetchUnreadArticleIDsAsync().isEmpty)
		#expect(try await database.fetchUnreadCountAsync(feedID: "feed") == 0)
		try await database.createStatusesIfNeededAsync(articleIDs: ["stored"])
		_ = try await database.markAndFetchNewAsync(articleIDs: ["stored"], statusKey: .starred, flag: true)
		#expect(try await database.fetchStarredArticleIDsAsync() == ["stored"])
		database.beginClosing()
		await #expect(throws: CancellationError.self) { _ = try await database.fetchStarredArticleIDsAsync() }
		await #expect(throws: CancellationError.self) { _ = try await database.fetchArticlesAsync(feedID: "feed") }
		await #expect(throws: CancellationError.self) { _ = try await database.fetchUnreadCountAsync(feedID: "feed") }
		await #expect(throws: CancellationError.self) { _ = try await database.markAndFetchNewAsync(articleIDs: ["stored"], statusKey: .starred, flag: false) }
		#expect(throws: CancellationError.self) { _ = try database.fetchArticles(feedID: "feed") }
		#expect(await database.close())
	}

	@Test func closedQueueRejectsReadAndNewStatusCallbacks() async {
		let queue = DatabaseQueue(databasePath: ":memory:")
		let table = ArticlesTable(name: "articles", accountID: "queue-read-fixture", queue: queue, retentionStyle: .feedBased)
		#expect(await queue.close())
		let articles: Result<Set<Article>, Error> = await withCheckedContinuation { continuation in
			table.fetchArticlesAsync("feed") { continuation.resume(returning: $0) }
		}
		if case .failure(let error) = articles { #expect(error is CancellationError) }
		else { Issue.record("Closed queue returned successful articles") }
		let ids: Result<Set<String>, Error> = await withCheckedContinuation { continuation in
			table.fetchUnreadArticleIDsAsync { continuation.resume(returning: $0) }
		}
		if case .failure(let error) = ids { #expect(error is CancellationError) }
		else { Issue.record("Closed queue returned successful IDs") }
		let marked: Result<Set<String>, Error> = await withCheckedContinuation { continuation in
			table.markAndFetchNew(["stored"], .starred, false) { continuation.resume(returning: $0) }
		}
		if case .failure(let error) = marked { #expect(error is CancellationError) }
		else { Issue.record("Closed queue returned a successful status write") }
	}

}
