import Foundation
import Testing
import RSDatabase
import Articles
@testable import ArticlesDatabase

@MainActor @Suite struct AdmissionCancellationTests {
	@Test func emptyCountsSucceedButClosedDatabaseRejects() async throws {
		let database = ArticlesDatabase(databaseFilePath: ":memory:", accountID: "counts-fixture", retentionStyle: .feedBased)
		let empty = try await database.fetchArticleCountsAsync(feedIDs: [])
		#expect(empty.totalCount == 0 && empty.statusesCount == 0)
		#expect(try await database.fetchLastUpdateDates().isEmpty)
		#expect(await database.createStatusesIfNeededAsync(articleIDs: ["stored"]))
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
		#expect(await database.createStatusesIfNeededAsync(articleIDs: ["stored"]))
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
}
