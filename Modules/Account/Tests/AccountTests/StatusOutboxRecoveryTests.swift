import Foundation
import Synchronization
import Testing
import Articles
import RSWeb
import Secrets
import SyncDatabase
@testable import Account

@Suite(.isolatedWebserviceResponses) @MainActor struct StatusOutboxRecoveryTests {
	private func configure(_ account: Account) async throws -> SyncDatabase {
		let sync: SyncDatabase
		switch account.delegate {
		case let delegate as FeedbinAccountDelegate:
			await delegate.waitForSyncInitializationForTesting()
			sync = delegate.syncDatabase
		case let delegate as FeedlyAccountDelegate:
			delegate.credentials = Credentials(type: .oauthAccessToken, username: "fixture", secret: "synthetic-token")
			sync = delegate.syncDatabaseForTesting
		case let delegate as NewsBlurAccountDelegate:
			sync = delegate.syncDatabase
		case let delegate as ReaderAPIAccountDelegate:
			account.endpointURL = URL(string: "https://fixture.invalid/reader/api/0")
			delegate.credentials = Credentials(type: .readerAPIKey, username: "fixture", secret: "synthetic-token")
			TestingURLProtocol.setResponse(.init(data: Data("synthetic-write-token".utf8)), forURLContaining: "/token")
			sync = delegate.syncDatabaseForTesting
		default:
			throw CocoaError(.featureUnsupported)
		}
		try await sync.resetAllSelectedForProcessingAndWait()
		return sync
	}

	@Test(arguments: [AccountType.feedbin, .feedly, .newsBlur, .freshRSS], [ArticleStatus.Key.read, .starred])
	func queueFailureKeepsIntentAcrossRestartAndIdenticalMark(type: AccountType, key: ArticleStatus.Key) async throws {
		let manager = TestAccountManager()
		let account = manager.createAccount(type: type)
		let sync = try await configure(account)
		let articleID = type == .newsBlur ? "1:42" : "42"
		let flag = key == .starred
		try await account.database.createStatusesIfNeededAsync(articleIDs: [articleID])
		// Both old inverse compensation and every queue insertion would fail after the local commit.
		#expect(account.database.executeSQLForTesting("CREATE TRIGGER fixture_no_inverse BEFORE UPDATE OF \(key.rawValue) ON statuses WHEN NEW.\(key.rawValue) = \(flag ? 0 : 1) BEGIN SELECT RAISE(ABORT, 'inverse denied'); END;"))
		#expect(await sync.executeSQLForTesting("CREATE TRIGGER fixture_no_queue BEFORE INSERT ON syncStatus BEGIN SELECT RAISE(ABORT, 'queue denied'); END;"))
		for _ in 0..<2 {
			do { try await account.markArticles(articleIDs: [articleID], statusKey: key, flag: flag); Issue.record("Queue failure reported success") }
			catch let error as SyncDatabaseError {
				if case .sqliteError(_, let code, let message) = error { #expect(code == 19 && message.contains("queue denied")) }
			}
		}
		let pending = try await account.database.pendingSyncStatuses()
		#expect(pending.count == 1 && pending.first?.articleID == articleID && pending.first?.key == key && pending.first?.flag == flag)
		#expect(try await sync.selectPendingCount() == 0)
		#expect(await account.closeForFixtureRemoval())

		let restarted = Account(dataFolder: account.dataFolder, type: type, accountID: account.accountID)
		let restartedSync = try await configure(restarted)
		#expect(try await restarted.database.pendingSyncStatuses().count == 1)
		#expect(await restartedSync.executeSQLForTesting("DROP TRIGGER fixture_no_queue"))
		let queued = NotificationCounter()
		let observer = NotificationCenter.default.addObserver(forName: .AccountDidQueueArticleStatuses, object: restarted, queue: nil) { _ in queued.count.withLock { $0 += 1 } }
		defer { NotificationCenter.default.removeObserver(observer) }
		// There are no changed IDs on this repeat. The journal still reconstructs the outbox.
		try await restarted.markArticles(articleIDs: [articleID], statusKey: key, flag: flag)
		#expect(queued.count.withLock { $0 } == 1)
		#expect(try await restarted.database.pendingSyncStatuses().isEmpty)
		#expect(try await restartedSync.selectPendingCount() == 1)
		#expect(try await restartedSync.selectPendingCount() == 1)
		let local: Set<String>
		if key == .read { local = try await restarted.fetchUnreadArticleIDsAsync() }
		else { local = try await restarted.fetchStarredArticleIDsAsync() }
		#expect(local.contains(articleID))
		try await manager.deleteAccount(restarted)
	}

	@Test func journalFailureRollsBackLocalStatusAndCachedFlags() async throws {
		let manager = TestAccountManager()
		try await manager.withAccount(type: .feedbin) { account in
			let sync = try await configure(account)
			try await account.database.createStatusesIfNeededAsync(articleIDs: ["42"])
			#expect(account.database.executeSQLForTesting("CREATE TRIGGER fixture_no_journal BEFORE INSERT ON pendingSyncStatuses BEGIN SELECT RAISE(ABORT, 'journal denied'); END;"))
			do { try await account.markArticles(articleIDs: ["42"], statusKey: .starred, flag: true); Issue.record("Journal failure exposed local status") }
			catch { #expect((error as NSError).code == 19) }
			#expect(try await account.fetchStarredArticleIDsAsync().isEmpty)
			#expect(try await account.database.pendingSyncStatuses().isEmpty)
			#expect(try await sync.selectPendingCount() == 0)
			#expect(account.database.executeSQLForTesting("DROP TRIGGER fixture_no_journal"))
			try await account.markArticles(articleIDs: ["42"], statusKey: .starred, flag: true)
			#expect(try await sync.selectPendingStarredStatusArticleIDs() == ["42"])
		}
	}

	@Test(arguments: [AccountType.feedbin, .feedly, .newsBlur, .freshRSS], [ArticleStatus.Key.read, .starred])
	func oldHTTPResponseCannotUndoAcknowledgedMark(type: AccountType, key: ArticleStatus.Key) async throws {
		let manager = TestAccountManager()
		try await manager.withAccount(type: type) { account in
			let sync = try await configure(account)
			let articleID = type == .newsBlur ? "1:42" : "42"
			let otherID = type == .newsBlur ? "1:99" : "99"
			try await account.database.createStatusesIfNeededAsync(articleIDs: [articleID, otherID])
			_ = try await account.updateStatusesAsync(articleIDs: [otherID], statusKey: key, flag: key == .starred)
			let (fetched, fetchedSignal) = AsyncStream<Void>.makeStream()
			let (release, releaseSignal) = AsyncStream<Void>.makeStream()
			let pause: @MainActor @Sendable () async -> Void = {
				fetchedSignal.yield(())
				for await _ in release { break }
			}
			let empty = Data("[]".utf8)
			switch type {
			case .feedbin:
				TestingURLProtocol.setResponse(.init(data: empty), forURLContaining: "unread_entries.json", httpMethod: "GET")
				TestingURLProtocol.setResponse(.init(data: empty), forURLContaining: "starred_entries.json", httpMethod: "GET")
				TestingURLProtocol.setResponse(.init(data: empty, headers: ["ETag": "fixture-old"], beforeResponse: pause), forURLContaining: key == .read ? "unread_entries.json" : "starred_entries.json", httpMethod: "GET")
			case .feedly:
				TestingURLProtocol.setResponse(.init(data: Data("{\"ids\":[]}".utf8), beforeResponse: pause), forURLContaining: "/v3/streams/ids")
			case .newsBlur:
				TestingURLProtocol.setResponse(.init(data: Data("{\"unread_feed_story_hashes\":{\"1\":[]}}".utf8)), forURLContaining: "reader/unread_story_hashes")
				TestingURLProtocol.setResponse(.init(data: Data("{\"starred_story_hashes\":[]}".utf8)), forURLContaining: "reader/starred_story_hashes")
				let body = key == .read ? "{\"unread_feed_story_hashes\":{\"1\":[]}}" : "{\"starred_story_hashes\":[]}"
				TestingURLProtocol.setResponse(.init(data: Data(body.utf8), beforeResponse: pause), forURLContaining: key == .read ? "reader/unread_story_hashes" : "reader/starred_story_hashes")
			case .freshRSS:
				// The read response is fetched first; the shared lifetime spans both kinds.
				TestingURLProtocol.setResponse(.init(data: Data("{\"itemRefs\":[]}".utf8), beforeResponse: pause), forURLContaining: "stream/items/ids")
			default: throw CocoaError(.featureUnsupported)
			}
			let refresh = Task {
				switch account.delegate {
				case let delegate as FeedbinAccountDelegate: try await delegate.refreshArticleStatus()
				case let delegate as NewsBlurAccountDelegate: try await delegate.refreshArticleStatus()
				case let delegate as ReaderAPIAccountDelegate: try await delegate.refreshArticleStatus()
				case let delegate as FeedlyAccountDelegate: try await delegate.refreshArticleStatus()
				default: throw CocoaError(.featureUnsupported)
				}
			}
			for await _ in fetched { break }
			// This must finish while the network response is paused: fetch owns no status gate.
			try await account.markArticles(articleIDs: [articleID], statusKey: key, flag: key == .starred)
			let acknowledged = try await sync.selectForProcessing()
			try await sync.deleteSelectedForProcessingOrThrow(Set(acknowledged.map(\.articleID)))
			#expect(try await sync.selectPendingCount() == 0)
			releaseSignal.finish()
			try await refresh.value
			let local: Set<String>
			if key == .read { local = try await account.fetchUnreadArticleIDsAsync() }
			else { local = try await account.fetchStarredArticleIDsAsync() }
			#expect(local.contains(articleID))
			#expect(!local.contains(otherID))
			if let delegate = account.delegate as? FeedbinAccountDelegate {
				let validatorKey = key == .read ? FeedbinAPICaller.ConditionalGetKeys.unreadEntries : FeedbinAPICaller.ConditionalGetKeys.starredEntries
				#expect(delegate.accountSettings?.conditionalGetInfo(for: validatorKey)?.etag == "fixture-old")
			}
		}
	}

	@Test func failedJournalCleanupKeepsRetryAndSignalsCommittedOutbox() async throws {
		let manager = TestAccountManager()
		try await manager.withAccount(type: .feedbin) { account in
			let sync = try await configure(account)
			try await account.database.createStatusesIfNeededAsync(articleIDs: ["42"])
			#expect(account.database.executeSQLForTesting("CREATE TRIGGER fixture_keep_journal BEFORE DELETE ON pendingSyncStatuses BEGIN SELECT RAISE(ABORT, 'cleanup denied'); END;"))
			let queued = NotificationCounter()
			let observer = NotificationCenter.default.addObserver(forName: .AccountDidQueueArticleStatuses, object: account, queue: nil) { _ in queued.count.withLock { $0 += 1 } }
			defer { NotificationCenter.default.removeObserver(observer) }
			do { try await account.markArticles(articleIDs: ["42"], statusKey: .starred, flag: true); Issue.record("Journal cleanup error was hidden") }
			catch { #expect((error as NSError).code == 19) }
			#expect(queued.count.withLock { $0 } == 1)
			#expect(try await sync.selectPendingStarredStatusArticleIDs() == ["42"])
			#expect(try await account.database.pendingSyncStatuses().count == 1)
			#expect(account.database.executeSQLForTesting("DROP TRIGGER fixture_keep_journal"))
			try await account.transferPendingSyncStatuses(to: sync)
			let acknowledged = try await sync.selectForProcessing()
			try await sync.deleteSelectedForProcessingOrThrow(Set(acknowledged.map(\.articleID)))
			#expect(try await sync.selectPendingCount() == 0)
			#expect(try await account.database.pendingSyncStatuses().isEmpty)
			#expect(try await account.fetchStarredArticleIDsAsync() == ["42"])
		}
	}

	private final class NotificationCounter: Sendable { let count = Synchronization.Mutex(0) }
}
