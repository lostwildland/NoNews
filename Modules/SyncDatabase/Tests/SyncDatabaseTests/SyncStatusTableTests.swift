//
//  SyncStatusTableTests.swift
//  SyncDatabase
//
//  Created by Brent Simmons on 8/30/26.
//

import Foundation
import Testing
import SyncDatabase
import Synchronization

@Suite struct SyncStatusTableTests {

	@Test func insertCommitFailureRollsBackAndKeepsExistingSelectedStatus() async throws {
		let database = SyncDatabase(databasePath: ":memory:")
		#expect(await database.insertStatuses([SyncStatus(articleID: "existing", key: .read, flag: true, selected: true)]))
		#expect(await database.executeSQLForTesting("PRAGMA foreign_keys=ON; CREATE TABLE fixture_parent (id INTEGER PRIMARY KEY); CREATE TABLE fixture_child (id INTEGER REFERENCES fixture_parent(id) DEFERRABLE INITIALLY DEFERRED); CREATE TRIGGER fixture_insert AFTER INSERT ON syncStatus BEGIN INSERT INTO fixture_child VALUES (1); END;"))
		#expect(!(await database.insertStatuses([SyncStatus(articleID: "failed", key: .starred, flag: true)])))
		let error = await database.lastErrorForTesting
		if case .sqliteError(_, let code, _)? = error { #expect(code == 19) }
		else { Issue.record("insertStatuses did not preserve its SQLite error") }
		#expect(try await database.selectForProcessing().contains { $0.articleID == "existing" && $0.selected })
		#expect(await database.executeSQLForTesting("DROP TRIGGER fixture_insert; DROP TABLE fixture_child; DROP TABLE fixture_parent;"))
		#expect(await database.insertStatuses([SyncStatus(articleID: "succeeded", key: .starred, flag: true)]))
		#expect(try await database.selectForProcessing().contains { $0.articleID == "succeeded" })
		#expect(await database.close())
	}

	@Test func fetchProtectionSurvivesAcknowledgementAndIsScopedToItsResponse() async throws {
		let database = SyncDatabase(databasePath: ":memory:")
		try await database.insertStatusesOrThrow([SyncStatus(articleID: "already-pending", key: .read, flag: true)])
		try await database.withStatusFetch {
			try await database.withStatusMutation {
				try await database.insertStatusesOrThrow([SyncStatus(articleID: "marked-during-fetch", key: .starred, flag: true)])
				let selected = try await database.selectForProcessing()
				try await database.deleteSelectedForProcessingOrThrow(Set(selected.map { $0.articleID }))
			}
			#expect(try await database.selectPendingCount() == 0)
			#expect(try await database.protectedStatusArticleIDs(key: .read) == ["already-pending"])
			#expect(try await database.protectedStatusArticleIDs(key: .starred) == ["marked-during-fetch"])
			// A later response must not inherit protection from an older overlapping fetch.
			try await database.withStatusFetch {
					let protectedRead = try await database.protectedStatusArticleIDs(key: .read)
					let protectedStarred = try await database.protectedStatusArticleIDs(key: .starred)
					#expect(protectedRead.isEmpty)
					#expect(protectedStarred.isEmpty)
			}
		}
		for cancel in [false, true] {
			do {
				try await database.withStatusFetch {
					if cancel { throw CancellationError() }
					throw SyncDatabaseError.sqliteError(operation: "fixture", code: 19, message: "fixture")
				}
			} catch { #expect((error is CancellationError) == cancel) }
		}
		#expect(try await database.protectedStatusArticleIDs(key: .read).isEmpty)
		#expect(await database.close())
	}

	@Test func resetWaitsForInFlightSendAcknowledgement() async throws {
		let database = SyncDatabase(databasePath: ":memory:")
		try await database.insertStatusesOrThrow([SyncStatus(articleID: "sent", key: .read, flag: true)])
		let (selected, selectedSignal) = AsyncStream<Void>.makeStream()
		let (acknowledge, acknowledgeSignal) = AsyncStream<Void>.makeStream()
		let (resetStarted, resetSignal) = AsyncStream<Void>.makeStream()
		let sender = Task {
			try await database.withStatusMutation {
				#expect(try await database.selectForProcessing().count == 1)
				selectedSignal.yield(())
				for await _ in acknowledge { break }
				try await database.deleteSelectedForProcessingOrThrow(["sent"], key: .read)
			}
		}
		for await _ in selected { break }
		database.setResetHookForTesting { resetSignal.yield(()) }
		let reset = Task { try await database.resetAllSelectedForProcessingAndWait() }
			for await _ in resetStarted { break }
		acknowledgeSignal.finish()
		try await sender.value
		try await reset.value
		database.setResetHookForTesting(nil)
		#expect(try await database.selectPendingCount() == 0)
		#expect(await database.close())
	}

	@Test func cancelledAcceptedResetDrainsBeforeCloseAndRecoversAfterRestart() async throws {
		let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
		try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
		let path = folder.appendingPathComponent("Sync.sqlite3").path
		let database = SyncDatabase(databasePath: path)
		try await database.insertStatusesOrThrow([SyncStatus(articleID: "retry", key: .starred, flag: true, selected: true)])
		let (started, startedSignal) = AsyncStream<Void>.makeStream()
		let (release, releaseSignal) = AsyncStream<Void>.makeStream()
		database.setResetHookForTesting {
			startedSignal.yield(())
			for await _ in release { break }
		}
		let reset = Task { try await database.resetAllSelectedForProcessingAndWait() }
		for await _ in started { break }
		reset.cancel()
		database.beginClosing()
		let close = Task { await database.close() }
		releaseSignal.finish()
		try await reset.value
		#expect(await close.value)
		let restarted = SyncDatabase(databasePath: path)
		#expect(try await restarted.selectForProcessing().contains { $0.articleID == "retry" && $0.selected })
		try await restarted.deleteSelectedForProcessingOrThrow(["retry"], key: .starred)
		#expect(try await restarted.selectPendingCount() == 0)
		#expect(await restarted.close())
		try FileManager.default.removeItem(at: folder)
	}

	@Test func restartRecoversRowsSelectedByInterruptedSender() async throws {
		let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
		try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
		let path = folder.appendingPathComponent("Sync.sqlite3").path
		let first = SyncDatabase(databasePath: path)
		try await first.insertStatusesOrThrow([SyncStatus(articleID: "interrupted", key: .read, flag: false)])
		#expect(try await first.selectForProcessing().count == 1)
		#expect(await first.close())
		let restarted = SyncDatabase(databasePath: path)
		try await restarted.resetAllSelectedForProcessingAndWait()
		try await restarted.deleteSelectedForProcessingOrThrow(["interrupted"])
		#expect(try await restarted.selectPendingCount() == 1)
		#expect(try await restarted.selectForProcessing().contains { $0.articleID == "interrupted" && !$0.flag })
		try await restarted.deleteSelectedForProcessingOrThrow(["interrupted"])
		#expect(try await restarted.selectPendingCount() == 0)
		#expect(await restarted.close())
		try FileManager.default.removeItem(at: folder)
	}

	@Test func resetPreservesActualSQLiteCommitError() async throws {
		let database = SyncDatabase(databasePath: ":memory:")
		try await database.insertStatusesOrThrow([SyncStatus(articleID: "retry", key: .read, flag: true, selected: true)])
		#expect(await database.executeSQLForTesting("PRAGMA foreign_keys=ON; CREATE TABLE fixture_parent (id INTEGER PRIMARY KEY); CREATE TABLE fixture_child (id INTEGER REFERENCES fixture_parent(id) DEFERRABLE INITIALLY DEFERRED); CREATE TRIGGER fixture_reset AFTER UPDATE OF selected ON syncStatus BEGIN INSERT INTO fixture_child VALUES (1); END;"))
		do { try await database.resetAllSelectedForProcessingAndWait(); Issue.record("Reset commit failure reported success") }
		catch let error as SyncDatabaseError {
			if case .sqliteError(_, let code, _) = error { #expect(code == 19) }
		}
		#expect(await database.executeSQLForTesting("DROP TRIGGER fixture_reset; DROP TABLE fixture_child; DROP TABLE fixture_parent;"))
		try await database.deleteSelectedForProcessingOrThrow(["retry"], key: .read)
		#expect(try await database.selectPendingCount() == 0)
		#expect(await database.close())
	}

	@Test func statusMutationGateSerializesConcurrentWriters() async {
		let database = SyncDatabase(databasePath: ":memory:")
		let (started, startedSignal) = AsyncStream<Void>.makeStream()
		let (release, releaseSignal) = AsyncStream<Void>.makeStream()
		let secondStarted = Mutex(false)
		let first = Task {
			await database.withStatusMutation {
				startedSignal.yield(())
				for await _ in release { break }
			}
		}
		for await _ in started { break }
		let second = Task {
			await database.withStatusMutation { secondStarted.withLock { $0 = true } }
		}
		await Task.yield()
		#expect(!secondStarted.withLock { $0 })
		releaseSignal.finish()
		await first.value
		await second.value
		#expect(secondStarted.withLock { $0 })
		#expect(await database.close())
	}

	@Test func selectionCommitFailureRollsBackSelectionAndKeepsQueueUsable() async throws {
		let fixture = SyncDatabase(databasePath: ":memory:")
		#expect(await fixture.insertStatuses([SyncStatus(articleID: "pending", key: .read, flag: true)]))
		#expect(await fixture.executeSQLForTesting("PRAGMA foreign_keys=ON; CREATE TABLE fixture_parent (id INTEGER PRIMARY KEY); CREATE TABLE fixture_child (id INTEGER REFERENCES fixture_parent(id) DEFERRABLE INITIALLY DEFERRED); CREATE TRIGGER fixture_select AFTER UPDATE OF selected ON syncStatus BEGIN INSERT INTO fixture_child VALUES (1); END;"))
		await #expect(throws: SyncDatabaseError.self) { _ = try await fixture.selectForProcessing() }
		#expect(await fixture.executeSQLForTesting("DROP TRIGGER fixture_select; DROP TABLE fixture_child; DROP TABLE fixture_parent;"))
		#expect(try await fixture.selectForProcessing().contains { $0.articleID == "pending" && $0.selected })
		#expect(await fixture.close())
	}

	private let database = SyncDatabase(databasePath: ":memory:")

	@Test func cachedStatusQueriesReportStepFailure() async throws {
		let fixture = SyncDatabase(databasePath: ":memory:")
		#expect(try await fixture.selectPendingReadStatusArticleIDs().isEmpty)
		#expect(try await fixture.selectPendingStarredStatusArticleIDs().isEmpty)
		#expect(try await fixture.selectForProcessing().isEmpty)
		#expect(await fixture.setStatusTableUnavailableForTesting(true))
		await #expect(throws: SyncDatabaseError.self) { _ = try await fixture.selectPendingReadStatusArticleIDs() }
		await #expect(throws: SyncDatabaseError.self) { _ = try await fixture.selectPendingStarredStatusArticleIDs() }
		await #expect(throws: SyncDatabaseError.self) { _ = try await fixture.selectForProcessing() }
		#expect(await fixture.setStatusTableUnavailableForTesting(false))
		#expect(await fixture.close())
	}

	/// Status syncing has to keep working on queues larger than SQLite’s
	/// expression-depth limit of 1000 terms.
	@Test func selectForProcessingHandlesLargeQueue() async throws {
		let articleIDCount = 1200
		let articleIDs = (0..<articleIDCount).map { "article-\($0)" }
		var statuses = Set<SyncStatus>()
		for articleID in articleIDs {
			statuses.insert(SyncStatus(articleID: articleID, key: .read, flag: true))
			statuses.insert(SyncStatus(articleID: articleID, key: .starred, flag: true))
		}
		await database.insertStatuses(statuses)

		let selectedStatuses = try await database.selectForProcessing()
		#expect(selectedStatuses.count == articleIDCount * 2)

		// Only rows marked selected in the database are deleted, so an empty
		// pending count is what proves the marking happened.
		await database.deleteSelectedForProcessing(Set(articleIDs))
		#expect(try await database.selectPendingCount() == 0)
	}

	@Test func selectForProcessingRespectsLimit() async throws {
		let limit = 150
		let statuses = Set((0..<300).map { SyncStatus(articleID: "article-\($0)", key: .read, flag: true) })
		await database.insertStatuses(statuses)

		let selectedStatuses = try await database.selectForProcessing(limit: limit)
		#expect(selectedStatuses.count == limit)
	}

	@Test func selectForProcessingMatchesArticleIDAndKeyPairs() async throws {
		let articleID = "article-with-both"
		let statuses: Set<SyncStatus> = [
			SyncStatus(articleID: articleID, key: .read, flag: true),
			SyncStatus(articleID: articleID, key: .starred, flag: true)
		]
		await database.insertStatuses(statuses)

		let selectedStatuses = try await database.selectForProcessing()
		#expect(selectedStatuses.count == 2)

		await database.deleteSelectedForProcessing([articleID], key: .read)
		#expect(try await database.selectPendingCount() == 1)
		let pendingStarredArticleIDs = try await database.selectPendingStarredStatusArticleIDs()
		#expect(pendingStarredArticleIDs == [articleID])
	}

	/// The step check must not fire on a healthy read that simply found no rows.
	/// A false positive there would stop syncing outright.
	@Test func emptyQueueReadsCleanly() async throws {
		#expect(try await database.selectForProcessing().isEmpty)
		#expect(try await database.selectPendingCount() == 0)
		#expect(try await database.selectPendingReadStatusArticleIDs().isEmpty)
		#expect(try await database.selectPendingStarredStatusArticleIDs().isEmpty)

		// And again once rows have been queued and then cleared.
		let statuses = Set((0..<5).map { SyncStatus(articleID: "article-\($0)", key: .read, flag: true) })
		await database.insertStatuses(statuses)
		_ = try await database.selectForProcessing()
		await database.deleteSelectedForProcessing(Set(statuses.map { $0.articleID }), key: .read)

		#expect(try await database.selectForProcessing().isEmpty)
		#expect(try await database.selectPendingCount() == 0)
	}
}
