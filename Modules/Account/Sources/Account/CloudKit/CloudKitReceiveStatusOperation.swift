//
//  CloudKitReceiveStatusOperation.swift
//  Account
//
//  Created by Maurice Parker on 5/2/20.
//  Copyright © 2020 Ranchero Software, LLC. All rights reserved.
//

import Foundation
import os
import RSCore
import RSDatabase
import CloudKitSync
import ActivityLog

final class CloudKitReceiveStatusOperation: MainThreadOperation, @unchecked Sendable {
	@MainActor static func enqueue(articlesZone: CloudKitArticlesZone, accountID: String, accountDisplayName: String, queue: MainThreadOperationQueue) async throws {
		try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
			let op = CloudKitReceiveStatusOperation(articlesZone: articlesZone, accountID: accountID, accountDisplayName: accountDisplayName)
			op.completionBlock = { operation in
				if let error = op.failure { continuation.resume(throwing: error) }
				else if operation.isCanceled { continuation.resume(throwing: CancellationError()) }
				else { continuation.resume(returning: ()) }
			}
			queue.add(op)
		}
	}
	private weak var articlesZone: CloudKitArticlesZone?
	private let accountID: String
	private let accountDisplayName: String
	private static let logger = cloudKitLogger
	private let work = DatabaseWork.current
	private(set) var failure: Error?

	init(articlesZone: CloudKitArticlesZone, accountID: String, accountDisplayName: String) {
		self.articlesZone = articlesZone
		self.accountID = accountID
		self.accountDisplayName = accountDisplayName
		super.init(name: "CloudKitReceiveStatusOperation")
	}

	@MainActor override func run() {
		guard let articlesZone else {
			self.didComplete()
			return
		}

		DatabaseWork.$current.withValue(work) {
		Task { @MainActor in
			defer {
				self.didComplete()
			}

			let activityLog = ActivityLog.shared
			let taskNumber = activityLog.nextTaskNumberString()
			let activityID = activityLog.createActivity(owner: .account(accountID: accountID, displayName: accountDisplayName), kind: .refreshArticleStatuses, detail: "Receiving article statuses \(taskNumber)")
			activityLog.didStart(id: activityID)

			Self.logger.debug("iCloud: Refreshing article statuses")
			do {
				let totals = try await articlesZone.refreshArticles()
				Self.logger.debug("iCloud: Finished refreshing article statuses")
				activityLog.didComplete(id: activityID, message: cloudKitSyncMessage(changed: totals.changed, deleted: totals.deleted))
			} catch {
				self.failure = error
				Self.logger.error("iCloud: Receive status error: \(error.localizedDescription)")
				activityLog.didFail(id: activityID, error: error)
			}
		}
		}
	}
}
