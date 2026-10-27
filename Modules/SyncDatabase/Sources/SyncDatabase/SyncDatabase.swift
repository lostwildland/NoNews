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

public actor SyncDatabase {
	private let admission = Mutex<(closing: Bool, accountID: String?, sealed: Bool)>((false, nil, false))
	private nonisolated var acceptsWork: Bool { admission.withLock { !$0.sealed && (!$0.closing || ($0.accountID != nil && $0.accountID == DatabaseWork.current?.accountID && DatabaseWork.current?.isActive == true)) } }
	public nonisolated func beginClosing(accountID: String? = nil) {
		admission.withLock { state in
			if !state.closing { state = (true, accountID, false) }
		}
	}
	private let database: FMDatabase
	public nonisolated let databasePath: String

	private static let logger = Logger(subsystem: Logger.nnwSubsystem, category: "SyncDatabase")

	public init(databasePath: String) {
		let database = FMDatabase.openAndSetUpDatabase(path: databasePath)
		database.runCreateStatements(Self.tableCreationStatements)
		database.vacuumIfNeeded()

		self.database = database
		self.databasePath = databasePath
	}

	// MARK: - API

	public func vacuum() {
		guard acceptsWork else { return }
		database.vacuum()
	}

	@discardableResult public func insertStatuses(_ statuses: Set<SyncStatus>) -> Bool {
		guard acceptsWork else { return false }
		do {
			try SyncStatusTable.insertStatuses(statuses, database: database)
			return true
		} catch {
			Self.logger.error("\(#function, privacy: .public) — \(self.databasePath, privacy: .public) — \(error.localizedDescription, privacy: .public)")
			return false
		}
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

	nonisolated public func resetAllSelectedForProcessing() {
		guard acceptsWork else { return }
		Task { await resetAllSelectedForProcessingAndWait() }
	}

	public func resetAllSelectedForProcessingAndWait() {
		guard acceptsWork else { return }
		_resetAllSelectedForProcessing()
	}

	public func close() -> Bool {
		beginClosing()
		admission.withLock { $0.sealed = true }
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
		guard acceptsWork else { return false }
		do {
			try SyncStatusTable.deleteSelectedForProcessing(articleIDs, key: key, database: database)
			return true
		} catch {
			Self.logger.error("\(#function, privacy: .public) — \(self.databasePath, privacy: .public) — \(error.localizedDescription, privacy: .public)")
			return false
		}
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
