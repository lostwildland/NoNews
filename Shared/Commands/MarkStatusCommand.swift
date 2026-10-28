//
//  MarkStatusCommand.swift
//  NetNewsWire
//
//  Created by Brent Simmons on 10/26/17.
//  Copyright © 2017 Ranchero Software. All rights reserved.
//

import Foundation
import RSCore
import Articles
import Account

// Mark articles read/unread, starred/unstarred, deleted/undeleted.

@MainActor final class MarkStatusCommand: UndoableCommand {

	let undoActionName: String
	let redoActionName: String
	var articleIDsByAccountID: [String: Set<String>]
	let undoManager: UndoManager
	let flag: Bool
	let statusKey: ArticleStatus.Key
	var completion: ((ArticleMarkResult) -> Void)?
	private var pendingMark: Task<[String: Set<String>], Never>?
	#if DEBUG
	var accountResolverForTesting: ((String) -> Account?)?
	var onMarkFinishedForTesting: ((ArticleMarkResult) -> Void)?
	var beforeMarkForTesting: ((Bool) async -> Void)?
	#endif
	// Called after every mark, with the flag that was applied, so undo and redo can update
	// the UI in the right direction. Unlike completion, it’s not one-shot.
	let didMark: ((Bool, [String: Set<String>]) -> Void)?

	init?(initialArticles: [Article], statusKey: ArticleStatus.Key, flag: Bool, undoManager: UndoManager, completion: ((ArticleMarkResult) -> Void)? = nil, didMark: ((Bool, [String: Set<String>]) -> Void)? = nil) {

        // Filter out articles that already have the desired status or can’t be marked.
		let articlesToMark = MarkStatusCommand.filteredArticles(initialArticles, statusKey, flag)
		if articlesToMark.isEmpty {
			return nil
		}
		self.articleIDsByAccountID = Dictionary(grouping: articlesToMark, by: { $0.accountID }).mapValues { Set($0.articleIDs()) }

		self.flag = flag
		self.statusKey = statusKey
 		self.undoManager = undoManager
		self.completion = completion
		self.didMark = didMark

		let actionName = MarkStatusCommand.actionName(statusKey, flag)
		self.undoActionName = actionName
		self.redoActionName = actionName
    }

	convenience init?(initialArticles: [Article], markingRead: Bool, undoManager: UndoManager, completion: ((ArticleMarkResult) -> Void)? = nil) {
		self.init(initialArticles: initialArticles, statusKey: .read, flag: markingRead, undoManager: undoManager, completion: completion)
	}

	convenience init?(initialArticles: [Article], markingStarred: Bool, undoManager: UndoManager, completion: ((ArticleMarkResult) -> Void)? = nil) {
		self.init(initialArticles: initialArticles, statusKey: .starred, flag: markingStarred, undoManager: undoManager, completion: completion)
	}

	func perform() {
		let isRedo = undoManager.isRedoing
		if isRedo { registerUndo() }
		mark(flag, registerAfterSuccess: !isRedo, registeredBefore: isRedo)
	}

	func undo() {
		registerRedo()
		mark(!flag, registerAfterSuccess: false, registeredBefore: true)
	}
}

@MainActor private extension MarkStatusCommand {
	func mark(_ flag: Bool, registerAfterSuccess: Bool, registeredBefore: Bool) {
		let previous = pendingMark
		let initialIDs = articleIDsByAccountID
		let completion = self.completion
		self.completion = nil
		let task = Task { @MainActor [self] in
			let ids = await previous?.value ?? initialIDs
			#if DEBUG
			await beforeMarkForTesting?(flag)
			#endif
			let outcome: ArticleMarkResult
			if ids.isEmpty {
				outcome = ArticleMarkResult()
			} else {
				#if DEBUG
				let resolver = accountResolverForTesting
				#else
				let resolver: ((String) -> Account?)? = nil
				#endif
				outcome = await withCheckedContinuation { continuation in
					markArticleIDs(ids, statusKey: statusKey, flag: flag, accountResolver: resolver) { continuation.resume(returning: $0) }
				}
			}
			articleIDsByAccountID = outcome.succeeded
			if outcome.succeeded.isEmpty {
				if registeredBefore { undoManager.removeAllActions(withTarget: self) }
			} else {
				if registerAfterSuccess { registerUndo() }
				didMark?(flag, outcome.succeeded)
			}
			completion?(outcome)
			#if DEBUG
			onMarkFinishedForTesting?(outcome)
			#endif
			return outcome.succeeded
		}
		pendingMark = task
	}

	static private let markReadActionName = NSLocalizedString("Mark Read", comment: "command")
	static private let markUnreadActionName = NSLocalizedString("Mark Unread", comment: "command")
	static private let markStarredActionName = NSLocalizedString("Mark Starred", comment: "command")
	static private let markUnstarredActionName = NSLocalizedString("Mark Unstarred", comment: "command")

	static func actionName(_ statusKey: ArticleStatus.Key, _ flag: Bool) -> String {

		switch statusKey {
		case .read:
			return flag ? markReadActionName : markUnreadActionName
		case .starred:
			return flag ? markStarredActionName : markUnstarredActionName
		}
	}

	static func filteredArticles(_ articles: [Article], _ statusKey: ArticleStatus.Key, _ flag: Bool) -> [Article] {
		articles.filter { article in
			guard article.status.boolStatus(forKey: statusKey) != flag else {
				return false
			}
			guard statusKey == .read else {
				return true
			}
			guard !article.status.read || article.isAvailableToMarkUnread else {
				return false
			}
			return true
		}
	}
}
