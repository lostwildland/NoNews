//
//  SyncDatabase.swift
//  NetNewsWire
//
//  Created by Maurice Parker on 5/14/19.
//  Copyright © 2019 Ranchero Software. All rights reserved.
//

import Foundation
import Synchronization
import os
import RSCore
import RSDatabase
import RSDatabaseObjC

private actor StatusMutationGate {
	private var held = false
	private var waiters = [CheckedContinuation<Void, Never>]()

	func acquire() async {
		if !held {
			held = true
			return
		}
		await withCheckedContinuation { continuation in
			waiters.append(continuation)
		}
	}

	func release() {
		if let continuation = waiters.first {
			waiters.removeFirst()
			continuation.resume()
		} else {
			held = false
		}
	}
}

public actor SyncDatabase {
	private struct Admission {
		var closing = false
		var accountID: String?
		var sealed = false
		var pendingResets = 0
		var drainWaiters = [CheckedContinuation<Void, Never>]()
	}
	private let admission = Mutex(Admission())
	#if DEBUG
	private let resetHook = Mutex<(@Sendable () async -> Void)?>(nil)
	public nonisolated func setResetHookForTesting(_ hook: (@Sendable () async -> Void)?) {
		resetHook.withLock { $0 = hook }
	}
	#endif
	private nonisolated var acceptsWork: Bool { admission.withLock { !$0.sealed && (!$0.closing || ($0.accountID != nil && $0.accountID == DatabaseWork.current?.accountID && DatabaseWork.current?.isActive == true)) } }
	public nonisolated func beginClosing(accountID: String? = nil) {
		admission.withLock { state in
			if !state.closing {
				state.closing = true
				state.accountID = accountID
			}
		}
	}
	private let database: FMDatabase
	private let statusMutationGate = StatusMutationGate()
	public nonisolated let databasePath: String

	private static let logger = Logger(subsystem: Logger.nnwSubsystem, category: "SyncDatabase")

	public init(databasePath: String) {
		let database = FMDatabase.openAndSetUpDatabase(path: databasePath)
		database.runCreateStatements(Self.tableCreationStatements)
		database.vacuumIfNeeded()

		self.database = database
		self.databasePath = databasePath
	}

	#if DEBUG
	public private(set) var lastErrorForTesting: SyncDatabaseError?
	public func executeSQLForTesting(_ sql: String) -> Bool { database.executeStatements(sql) }
	public func setStatusTableUnavailableForTesting(_ unavailable: Bool) -> Bool {
		database.executeStatements(unavailable ? "ALTER TABLE syncStatus RENAME TO fixture_saved_syncStatus" : "ALTER TABLE fixture_saved_syncStatus RENAME TO syncStatus")
	}
	#endif

	// MARK: - API

	public func vacuum() {
		guard acceptsWork else { return }
		database.vacuum()
	}

	@discardableResult public func insertStatuses(_ statuses: Set<SyncStatus>) -> Bool {
		do {
			try insertStatusesOrThrow(statuses)
			return true
		} catch {
			#if DEBUG
			lastErrorForTesting = error as? SyncDatabaseError
			#endif
			Self.logger.error("\(#function, privacy: .public) — \(self.databasePath, privacy: .public) — \(error.localizedDescription, privacy: .public)")
			return false
		}
	}

	public func insertStatusesOrThrow(_ statuses: Set<SyncStatus>) throws {
		guard acceptsWork else { throw CancellationError() }
		#if DEBUG
		lastErrorForTesting = nil
		#endif
		try SyncStatusTable.insertStatuses(statuses, database: database)
	}

	public func recoverStatusMutationFailure(_ statuses: Set<SyncStatus>, queueError: Error, compensate: @escaping @MainActor @Sendable () async throws -> Void, recovered: @escaping @MainActor @Sendable () async -> Void) async throws -> Never {
		do {
			try await compensate()
		} catch {
			let compensationFailure = error.localizedDescription
			do {
				try insertStatusesOrThrow(statuses)
			} catch {
				throw StatusMutationRecoveryError(queueFailure: queueError.localizedDescription, compensationFailure: compensationFailure, outboxFailure: error.localizedDescription)
			}
			await recovered()
			throw StatusMutationRecoveryError(queueFailure: queueError.localizedDescription, compensationFailure: compensationFailure, outboxFailure: nil)
		}
		throw queueError
	}

	public func selectForProcessing(limit: Int? = nil) throws -> Set<SyncStatus> {
		guard acceptsWork else { throw CancellationError() }
		return try SyncStatusTable.selectForProcessing(limit: limit, database: database)
	}

	public func selectPendingCount() throws -> Int {
		guard acceptsWork else { throw CancellationError() }
		return try SyncStatusTable.selectPendingCount(database: database)
	}

	public func selectPendingReadStatusArticleIDs() throws -> Set<String> {
		guard acceptsWork else { throw CancellationError() }
		return try SyncStatusTable.selectPendingReadStatusArticleIDs(database: database)
	}

	public func selectPendingStarredStatusArticleIDs() throws -> Set<String> {
		guard acceptsWork else { throw CancellationError() }
		return try SyncStatusTable.selectPendingStarredStatusArticleIDs(database: database)
	}

	/// Serializes a status mutation with CloudKit page application and other
	/// status writers so pending rows cannot change between the check and commit.
	public func withStatusMutation<T: Sendable>(_ operation: @escaping @MainActor @Sendable () async throws -> T) async rethrows -> T {
		await statusMutationGate.acquire()
		do {
			let result = try await operation()
			await statusMutationGate.release()
			return result
		} catch {
			await statusMutationGate.release()
			throw error
		}
	}

	@discardableResult nonisolated public func resetAllSelectedForProcessing() -> Bool {
		let accepted = admission.withLock { state in
			guard !state.sealed && (!state.closing || (state.accountID != nil && state.accountID == DatabaseWork.current?.accountID && DatabaseWork.current?.isActive == true)) else { return false }
			state.pendingResets += 1
			return true
		}
		guard accepted else { return false }
		#if DEBUG
		let hook = resetHook.withLock { $0 }
		#endif
		Task {
			#if DEBUG
			await hook?()
			#endif
			await performAcceptedReset()
			finishAcceptedReset()
		}
		return true
	}

	private func performAcceptedReset() { _resetAllSelectedForProcessing() }

	private nonisolated func finishAcceptedReset() {
		let waiters = admission.withLock { state -> [CheckedContinuation<Void, Never>] in
			state.pendingResets -= 1
			guard state.pendingResets == 0 && !state.drainWaiters.isEmpty else { return [] }
			state.sealed = true
			let waiters = state.drainWaiters
			state.drainWaiters.removeAll()
			return waiters
		}
		for waiter in waiters { waiter.resume() }
	}

	public func resetAllSelectedForProcessingAndWait() {
		guard acceptsWork else { return }
		_resetAllSelectedForProcessing()
	}

	public func close() async -> Bool {
		beginClosing()
		await withCheckedContinuation { continuation in
			let ready = admission.withLock { state in
				if state.pendingResets == 0 {
					state.sealed = true
					return true
				}
				state.drainWaiters.append(continuation)
				return false
			}
			if ready { continuation.resume() }
		}
		return database.close()
	}

	/// Pass `key` when sending one status kind at a time. A nil key matches all kinds —
	/// correct only when every queued kind for these articleIDs was sent together.
	@discardableResult public func resetSelectedForProcessing(_ articleIDs: Set<String>, key: SyncStatus.Key? = nil) -> Bool {
		guard acceptsWork else { return false }
		do {
			try SyncStatusTable.resetSelectedForProcessing(articleIDs, key: key, database: database)
			return true
		} catch {
			Self.logger.error("\(#function, privacy: .public) — \(self.databasePath, privacy: .public) — \(error.localizedDescription, privacy: .public)")
			return false
		}
	}

	@discardableResult public func deleteSelectedForProcessing(_ articleIDs: Set<String>, key: SyncStatus.Key? = nil) -> Bool {
		do {
			try deleteSelectedForProcessingOrThrow(articleIDs, key: key)
			return true
		} catch {
			Self.logger.error("\(#function, privacy: .public) — \(self.databasePath, privacy: .public) — \(error.localizedDescription, privacy: .public)")
			return false
		}
	}

	public func deleteSelectedForProcessingOrThrow(_ articleIDs: Set<String>, key: SyncStatus.Key? = nil) throws {
		guard acceptsWork else { throw CancellationError() }
		try SyncStatusTable.deleteSelectedForProcessing(articleIDs, key: key, database: database)
	}
}

// MARK: - Private

private extension SyncDatabase {

	static let tableCreationStatements = """
	CREATE TABLE if not EXISTS syncStatus (articleID TEXT NOT NULL, key TEXT NOT NULL, flag BOOL NOT NULL DEFAULT 0, selected BOOL NOT NULL DEFAULT 0, PRIMARY KEY (articleID, key));
	"""

	func _resetAllSelectedForProcessing() {
		do {
			try SyncStatusTable.resetAllSelectedForProcessing(database: database)
		} catch {
			Self.logger.error("\(#function, privacy: .public) — \(self.databasePath, privacy: .public) — \(error.localizedDescription, privacy: .public)")
		}
	}
}
