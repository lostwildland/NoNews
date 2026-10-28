//
//  SyncDatabaseError.swift
//  SyncDatabase
//
//  Created by Brent Simmons on 9/16/26.
//

import Foundation
import RSDatabaseObjC

/// Sync database failure.
///
/// Deliberately not localized (to be used with bug reports).
public enum SyncDatabaseError: LocalizedError {

	case sqliteError(operation: String, code: Int, message: String)

	public var errorDescription: String? {
		switch self {
		case .sqliteError(let operation, let code, let message):
			return "\(operation) failed — SQLite \(code): \(message)"
		}
	}
}

public struct StatusMutationRecoveryError: LocalizedError, Sendable {
	public let queueFailure: String
	public let compensationFailure: String
	public let outboxFailure: String?

	public var errorDescription: String? {
		var message = "Status mutation recovery failed: queue=\(queueFailure); compensation=\(compensationFailure)"
		if let outboxFailure { message += "; outbox=\(outboxFailure)" }
		return message
	}
}

extension FMDatabase {

	/// Current SQLite error. Call before `rollback()` which overwrites the last-error state.
	func syncDatabaseError(operation: String) -> SyncDatabaseError {
		SyncDatabaseError.sqliteError(operation: operation, code: Int(lastErrorCode()), message: lastErrorMessage() ?? "unknown")
	}
}
