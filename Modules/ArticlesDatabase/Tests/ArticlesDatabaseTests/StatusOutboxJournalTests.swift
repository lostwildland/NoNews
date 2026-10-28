import Foundation
import Testing
import Articles
import ArticlesDatabase
import RSParser

@MainActor
struct StatusOutboxJournalTests {
	@Test func statusAndIntentRollbackTogetherThenSurviveAnIdenticalRetry() async throws {
		let database = ArticlesDatabase(databaseFilePath: ":memory:", accountID: "fixture", retentionStyle: .feedBased)
		try await database.createStatusesIfNeededAsync(articleIDs: ["article"])
		#expect(database.executeSQLForTesting("CREATE TRIGGER fixture_journal_failure BEFORE INSERT ON pendingSyncStatuses BEGIN SELECT RAISE(ABORT, 'journal failed'); END;"))
		await #expect(throws: (any Error).self) {
			_ = try await database.markAsync(articleIDs: ["article"], statusKey: .starred, flag: true, queueForSync: true)
		}
		#expect(try await database.fetchStarredArticleIDsAsync().isEmpty)
		#expect(try await database.pendingSyncStatuses().isEmpty)
		#expect(database.executeSQLForTesting("DROP TRIGGER fixture_journal_failure"))

		let changed = try await database.markAsync(articleIDs: ["article"], statusKey: .starred, flag: true, queueForSync: true)
		#expect(changed == ["article"])
		#expect(try await database.pendingSyncStatuses().count == 1)
		let repeated = try await database.markAsync(articleIDs: ["article"], statusKey: .starred, flag: true, queueForSync: true)
		#expect(repeated.isEmpty)
		#expect(try await database.pendingSyncStatuses().count == 1)
		#expect(await database.close())
	}

	@Test func pendingIntentIsDurableAcrossArticlesDatabaseRestart() async throws {
		let folder = URL(fileURLWithPath: "/tmp/nonews-t30-r25-article-restart")
		try? FileManager.default.removeItem(at: folder)
		try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
		let path = folder.appendingPathComponent("Articles.sqlite3").path
		let first = ArticlesDatabase(databaseFilePath: path, accountID: "fixture", retentionStyle: .feedBased)
		try await first.createStatusesIfNeededAsync(articleIDs: ["article"])
		_ = try await first.markAsync(articleIDs: ["article"], statusKey: .read, flag: false, queueForSync: true)
		#expect(await first.close())

		let restarted = ArticlesDatabase(databaseFilePath: path, accountID: "fixture", retentionStyle: .feedBased)
		do {
			let pending = try await restarted.pendingSyncStatuses()
			let unread = try await restarted.fetchUnreadArticleIDsAsync()
			#expect(pending.count == 1)
			#expect(unread.contains("article"))
		} catch {
			Issue.record("restart read failed: \(error)")
		}
		#expect(await restarted.close())
		try FileManager.default.removeItem(at: folder)
	}
}
