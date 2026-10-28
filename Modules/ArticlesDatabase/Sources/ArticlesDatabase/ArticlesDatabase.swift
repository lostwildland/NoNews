//
//  ArticlesDatabase.swift
//  NetNewsWire
//
//  Created by Brent Simmons on 7/20/15.
//  Copyright © 2015 Ranchero Software, LLC. All rights reserved.
//

import Foundation
import os
import RSCore
import RSDatabase
import RSParser
import Articles

// This file is the entirety of the public API for ArticlesDatabase.framework.
// Everything else is implementation.

public typealias UnreadCountDictionary = [String: Int] // feedID: unreadCount

public struct ArticleChanges: Sendable {
	public let new: Set<Article>?
	public let updated: Set<Article>?
	public let deleted: Set<Article>?
	public let error: (any Error)?

	public init() {
		self.new = Set<Article>()
		self.updated = Set<Article>()
		self.deleted = Set<Article>()
		self.error = nil
	}

	public init(new: Set<Article>?, updated: Set<Article>?, deleted: Set<Article>?, error: (any Error)? = nil) {
		self.new = new
		self.updated = updated
		self.deleted = deleted
		self.error = error
	}
}

/// Aggregate counts for a single account's articles database.
public struct ArticleCounts: Sendable {
	public let totalCount: Int
	public let unreadCount: Int
	public let starredCount: Int
	public let statusesCount: Int
}

@MainActor public final class ArticlesDatabase {
	public enum RetentionStyle: Sendable {
		case feedBased // Local and iCloud: article retention is defined by contents of feed
		case syncSystem // Feedbin, Feedly, etc.: article retention is defined by external system
	}

	public nonisolated let databasePath: String

	private let articlesTable: ArticlesTable
	private let queue: DatabaseQueue
	private let retentionStyle: RetentionStyle
	private let accountID: String
	private var authorsMigration: Task<Void, Never>?
	private var closing = false
	private var sealed = false
	private var activeOperations = 0
	private var drainWaiters = [CheckedContinuation<Void, Never>]()
	private func operationFinished() {
		activeOperations -= 1
		if activeOperations == 0 {
			let waiters = drainWaiters
			drainWaiters.removeAll()
			for waiter in waiters { waiter.resume() }
		}
	}
	private var acceptsWork: Bool { !sealed && (!closing || DatabaseWork.current?.isActive == true && DatabaseWork.current?.accountID == accountID) }
	#if DEBUG
	public func executeSQLForTesting(_ sql: String) -> Bool {
		nonisolated(unsafe) var succeeded = false
		let accepted = queue.runInDatabaseSync { database in succeeded = database.executeStatements(sql) }
		return accepted && succeeded
	}
	public func setArticlesTableUnavailableForTesting(_ unavailable: Bool) -> Bool {
		nonisolated(unsafe) var succeeded = false
		let sql = unavailable ? "ALTER TABLE articles RENAME TO fixture_saved_articles" : "ALTER TABLE fixture_saved_articles RENAME TO articles"
		let accepted = queue.runInDatabaseSync { database in succeeded = database.executeStatements(sql) }
		return accepted && succeeded
	}
	public func setStatusTableUnavailableForTesting(_ unavailable: Bool) -> Bool {
		nonisolated(unsafe) var succeeded = false
		let sql = unavailable ? "ALTER TABLE statuses RENAME TO fixture_saved_statuses" : "ALTER TABLE fixture_saved_statuses RENAME TO statuses"
		let accepted = queue.runInDatabaseSync { database in
			succeeded = database.executeStatements(sql)
		}
		return accepted && succeeded
	}
	#endif
	public func beginClosing() {
		closing = true
		articlesTable.stopIndexing()
	}

	nonisolated private static let logger = Logger(subsystem: Logger.nnwSubsystem, category: "ArticlesDatabase")

	public init(databaseFilePath: String, accountID: String, retentionStyle: RetentionStyle) {
		Self.logger.debug("Articles Database init \(accountID, privacy: .public)")

		self.databasePath = databaseFilePath
		let queue = DatabaseQueue(databasePath: databaseFilePath)
		self.queue = queue
		self.articlesTable = ArticlesTable(name: DatabaseTableName.articles, accountID: accountID, queue: queue, retentionStyle: retentionStyle)
		self.retentionStyle = retentionStyle
		self.accountID = accountID

		queue.runCreateStatements(ArticlesDatabase.tableCreationStatements)
		queue.runInDatabase(onRejected: {}) { database in
			Self.logger.debug("ArticlesDatabase: creating tables \(accountID, privacy: .public)")
			if !self.articlesTable.containsColumn("searchRowID", in: database) {
				database.executeStatements("ALTER TABLE articles add column searchRowID INTEGER;")
			}
			if !self.articlesTable.containsColumn("markdown", in: database) {
				Self.logger.debug("ArticlesDatabase: adding markdown column \(accountID, privacy: .public)")
				database.executeStatements("ALTER TABLE articles add column markdown TEXT;")
			}
			if !self.articlesTable.containsColumn("authors", in: database) {
				Self.logger.debug("ArticlesDatabase: adding authors column \(accountID, privacy: .public)")
				database.executeStatements("ALTER TABLE articles add column authors TEXT;")
			}
			database.executeStatements("CREATE INDEX if not EXISTS articles_searchRowID on articles(searchRowID);")
			database.executeStatements("DROP TABLE if EXISTS tags;DROP INDEX if EXISTS tags_tagName_index;DROP INDEX if EXISTS articles_feedID_index;DROP INDEX if EXISTS statuses_read_index;DROP TABLE if EXISTS attachments;DROP TABLE if EXISTS attachmentsLookup;")
		}

		DispatchQueue.main.async {
			self.articlesTable.indexUnindexedArticles()
		}

		// Backfill the authors JSON column cooperatively, yielding between batches
		// so that other database work (fetches, etc.) can interleave.
		self.authorsMigration = Task.detached { [accountID, queue] in
			let migration = AuthorsSchemaMigration(accountID: accountID, queue: queue)
			await migration.run()
		}
	}

	public func close() async -> Bool {
		beginClosing()
		await authorsMigration?.value
		if activeOperations > 0 {
			await withCheckedContinuation { drainWaiters.append($0) }
		}
		sealed = true
		return await queue.close()
	}

	// MARK: - Vacuum

	public func vacuum() async {
		guard acceptsWork else { return }
		activeOperations += 1
		defer { operationFinished() }
		await queue.vacuum()
	}

	// MARK: - Repairing

	/// Repair status rows that disagree with their in-memory statuses,
	/// which can happen when a database write was lost.
	public func repairStatuses() {
		guard acceptsWork else { return }
		queue.runInDatabase(onRejected: {}) { database in
			self.articlesTable.repairStatuses(database)
		}
	}

	// MARK: - Fetching Articles

	public func fetchArticles(feedID: String) throws -> Set<Article> {
		guard acceptsWork else { throw CancellationError() }
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		return try articlesTable.fetchArticles(feedID)
	}

	public func fetchArticles(feedIDs: Set<String>) throws -> Set<Article> {
		guard acceptsWork else { throw CancellationError() }
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		return try articlesTable.fetchArticles(feedIDs)
	}

	public func fetchArticles(articleIDs: Set<String>) throws -> Set<Article> {
		guard acceptsWork else { throw CancellationError() }
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		return try articlesTable.fetchArticles(articleIDs: articleIDs)
	}

	public func fetchUnreadArticles(feedIDs: Set<String>, limit: Int? = nil) throws -> Set<Article> {
		guard acceptsWork else { throw CancellationError() }
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		return try articlesTable.fetchUnreadArticles(feedIDs, limit)
	}

	public func fetchTodayArticles(feedIDs: Set<String>, limit: Int? = nil) throws -> Set<Article> {
		guard acceptsWork else { throw CancellationError() }
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		return try articlesTable.fetchArticlesSince(feedIDs, todayCutoffDate(), limit)
	}

	public func fetchStarredArticles(feedIDs: Set<String>, limit: Int? = nil) throws -> Set<Article> {
		guard acceptsWork else { throw CancellationError() }
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		return try articlesTable.fetchStarredArticles(feedIDs, limit)
	}

	public func fetchStarredArticlesCount(feedIDs: Set<String>) throws -> Int {
		guard acceptsWork else { throw CancellationError() }
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		return try articlesTable.fetchStarredArticlesCount(feedIDs)
	}

	/// Returns aggregate article counts (total, unread, starred, statuses) for the given feeds.
	public func fetchArticleCountsAsync(feedIDs: Set<String>) async throws -> ArticleCounts {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		return try await withCheckedThrowingContinuation { continuation in
			articlesTable.fetchArticleCountsAsync(feedIDs) { articleCounts in
				continuation.resume(with: articleCounts)
			}
		}
	}

	public func fetchArticlesMatching(searchString: String, feedIDs: Set<String>) throws -> Set<Article> {
		guard acceptsWork else { throw CancellationError() }
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		return try articlesTable.fetchArticlesMatching(searchString, feedIDs)
	}

	public func fetchArticlesMatchingWithArticleIDs(searchString: String, articleIDs: Set<String>) throws -> Set<Article> {
		guard acceptsWork else { throw CancellationError() }
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		return try articlesTable.fetchArticlesMatchingWithArticleIDs(searchString, articleIDs)
	}

	/// Returns a dictionary of feedID → latest article date for all feeds with articles.
	public func fetchLastUpdateDates() async throws -> [String: Date] {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		return try await withCheckedThrowingContinuation { continuation in
			articlesTable.fetchLastUpdateDatesAsync { lastUpdateDates in
				continuation.resume(with: lastUpdateDates)
			}
		}
	}

	// MARK: - Fetching Articles Async

	public func fetchArticlesAsync(feedID: String) async throws -> Set<Article> {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		return try await withCheckedThrowingContinuation { continuation in
			_fetchArticlesAsync(feedID: feedID) { articles in
				continuation.resume(with: articles)
			}
		}
	}

	public func fetchArticlesAsync(feedIDs: Set<String>) async throws -> Set<Article> {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		return try await withCheckedThrowingContinuation { continuation in
			_fetchArticlesAsync(feedIDs: feedIDs) { articles in
				continuation.resume(with: articles)
			}
		}
	}

	public func fetchArticlesAsync(articleIDs: Set<String>) async throws -> Set<Article> {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		return try await withCheckedThrowingContinuation { continuation in
			_fetchArticlesAsync(articleIDs: articleIDs) { articles in
				continuation.resume(with: articles)
			}
		}
	}

	public func fetchUnreadArticlesAsync(feedIDs: Set<String>, limit: Int? = nil) async throws -> Set<Article> {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		return try await withCheckedThrowingContinuation { continuation in
			_fetchUnreadArticlesAsync(feedIDs: feedIDs, limit: limit) { articles in
				continuation.resume(with: articles)
			}
		}
	}

	public func fetchTodayArticlesAsync(feedIDs: Set<String>, limit: Int? = nil) async throws -> Set<Article> {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		return try await withCheckedThrowingContinuation { continuation in
			_fetchTodayArticlesAsync(feedIDs: feedIDs, limit: limit) { articles in
				continuation.resume(with: articles)
			}
		}
	}

	public func fetchedStarredArticlesAsync(feedIDs: Set<String>, limit: Int? = nil) async throws -> Set<Article> {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		return try await withCheckedThrowingContinuation { continuation in
			_fetchedStarredArticlesAsync(feedIDs: feedIDs, limit: limit) { articles in
				continuation.resume(with: articles)
			}
		}
	}

	public func fetchArticlesMatchingAsync(searchString: String, feedIDs: Set<String>) async throws -> Set<Article> {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		return try await withCheckedThrowingContinuation { continuation in
			_fetchArticlesMatchingAsync(searchString: searchString, feedIDs: feedIDs) { articles in
				continuation.resume(with: articles)
			}
		}
	}

	public func fetchArticlesMatchingWithArticleIDsAsync(searchString: String, articleIDs: Set<String>) async throws -> Set<Article> {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		return try await withCheckedThrowingContinuation { continuation in
			_fetchArticlesMatchingWithArticleIDsAsync(searchString: searchString, articleIDs: articleIDs) { articles in
				continuation.resume(with: articles)
			}
		}
	}

	// MARK: - Unread Counts

	/// Fetch all non-zero unread counts. Nil if the query fails.
	public func fetchAllUnreadCountsAsync() async -> UnreadCountDictionary? {
		guard acceptsWork else { return nil }
		activeOperations += 1
		defer { operationFinished() }
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		return await withCheckedContinuation { continuation in
			articlesTable.fetchAllUnreadCounts { unreadCountDictionary in
				continuation.resume(returning: unreadCountDictionary)
			}
		}
	}

	/// Fetch unread count for a single feed.
	public func fetchUnreadCountAsync(feedID: String) async throws -> Int {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		return try await withCheckedThrowingContinuation { continuation in
			_fetchUnreadCounts(feedIDs: Set([feedID])) { result in
				continuation.resume(with: result.map { $0[feedID] ?? 0 })
			}
		}
	}

	/// Fetch non-zero unread counts for given feedIDs.
	public func fetchUnreadCountsAsync(feedIDs: Set<String>) async throws -> UnreadCountDictionary {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		return try await withCheckedThrowingContinuation { continuation in
			_fetchUnreadCounts(feedIDs: feedIDs) { unreadCountDictionary in
				continuation.resume(with: unreadCountDictionary)
			}
		}
	}

	public func fetchUnreadCountForTodayAsync(feedIDs: Set<String>) async throws -> Int {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		return try await withCheckedThrowingContinuation { continuation in
			_fetchUnreadCount(feedIDs: feedIDs, since: todayCutoffDate()) { unreadCount in
				continuation.resume(with: unreadCount)
			}
		}
	}

	public func fetchUnreadCountForStarredArticlesAsync(feedIDs: Set<String>) async throws -> Int {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		return try await withCheckedThrowingContinuation { continuation in
			_fetchStarredAndUnreadCount(feedIDs: feedIDs) { unreadCount in
				continuation.resume(with: unreadCount)
			}
		}
	}

	public func fetchTodayArticlesCountAsync(feedIDs: Set<String>) async throws -> Int {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		return try await withCheckedThrowingContinuation { continuation in
			articlesTable.fetchArticlesCountSince(feedIDs, todayCutoffDate()) { count in
				continuation.resume(with: count)
			}
		}
	}

	public func fetchStarredArticlesCountAsync(feedIDs: Set<String>) async throws -> Int {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		return try await withCheckedThrowingContinuation { continuation in
			articlesTable.fetchStarredArticlesCountAsync(feedIDs) { count in
				continuation.resume(with: count)
			}
		}
	}

	// MARK: - Saving, Updating, and Deleting Articles

	/// Update articles and save new ones — for feed-based systems (local and iCloud).
	public func updateAsync(parsedItems: Set<ParsedItem>, feedID: String, deleteOlder: Bool) async -> ArticleChanges {
		guard acceptsWork else { return ArticleChanges(new: nil, updated: nil, deleted: nil, error: CancellationError()) }
		activeOperations += 1
		defer { operationFinished() }
		return await withCheckedContinuation { continuation in
			_update(parsedItems: parsedItems, feedID: feedID, deleteOlder: deleteOlder) { articleChanges in
				continuation.resume(returning: articleChanges)
			}
		}
	}

	/// Update articles and save new ones — for sync systems (Feedbin, Feedly, etc.).
	public func updateAsync(feedIDsAndItems: [String: Set<ParsedItem>], defaultRead: Bool) async -> ArticleChanges {
		guard acceptsWork else { return ArticleChanges(new: nil, updated: nil, deleted: nil, error: CancellationError()) }
		activeOperations += 1
		defer { operationFinished() }
		return await withCheckedContinuation { continuation in
			_update(feedIDsAndItems: feedIDsAndItems, defaultRead: defaultRead) { articleChanges in
				continuation.resume(returning: articleChanges)
			}
		}
	}

	/// Delete articles
	@discardableResult public func deleteAsync(articleIDs: Set<String>) async -> Bool {
		guard acceptsWork else { return false }
		activeOperations += 1
		defer { operationFinished() }
		return await withCheckedContinuation { continuation in
			_delete(articleIDs: articleIDs) { succeeded in
				continuation.resume(returning: succeeded)
			}
		}
	}

	// MARK: - ArticleIDs

	/// Fetch the articleIDs of unread articles.
	public func fetchUnreadArticleIDsAsync() async throws -> Set<String> {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		return try await withCheckedThrowingContinuation { continuation in
			_fetchUnreadArticleIDsAsync { articleIDs in
				continuation.resume(with: articleIDs)
			}
		}
	}

	public func fetchStarredArticleIDsAsync() async throws -> Set<String> {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		return try await withCheckedThrowingContinuation { continuation in
			_fetchStarredArticleIDsAsync { articleIDs in
				continuation.resume(with: articleIDs)
			}
		}
	}

	/// Fetch articleIDs for articles that we should have, but don’t. These articles are either starred or newer than the article cutoff date.
	public func fetchArticleIDsForStatusesWithoutArticlesNewerThanCutoffDateAsync() async throws -> Set<String> {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		return try await withCheckedThrowingContinuation { continuation in
			_fetchArticleIDsForStatusesWithoutArticlesNewerThanCutoffDate { articleIDs in
				continuation.resume(with: articleIDs)
			}
		}
	}

	// MARK: - Statuses

	/// Mark statuses for articleIDs. Returns the articleIDs whose status actually changed.
	public func markAsync(articleIDs: Set<String>, statusKey: ArticleStatus.Key, flag: Bool) async throws -> Set<String> {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		return try await withCheckedThrowingContinuation { continuation in
			_mark(articleIDs: articleIDs, statusKey: statusKey, flag: flag) { changedArticleIDs in
				continuation.resume(with: changedArticleIDs)
			}
		}
	}

	public func markAndFetchNewAsync(articleIDs: Set<String>, statusKey: ArticleStatus.Key, flag: Bool) async throws -> Set<String> {
		guard acceptsWork else { throw CancellationError() }
		activeOperations += 1
		defer { operationFinished() }
		return try await withCheckedThrowingContinuation { continuation in
			_markAndFetchNew(articleIDs: articleIDs, statusKey: statusKey, flag: flag) { articleIDs in
				continuation.resume(with: articleIDs)
			}
		}
	}

	/// Create statuses for specified articleIDs. For existing statuses, don’t do anything.
	/// For newly-created statuses, mark them as read and not-starred.
	@discardableResult public func createStatusesIfNeededAsync(articleIDs: Set<String>) async -> Bool {
		guard acceptsWork else { return false }
		activeOperations += 1
		defer { operationFinished() }
		await withCheckedContinuation { continuation in
			_createStatusesIfNeeded(articleIDs: articleIDs) {
				continuation.resume()
			}
		}
		return true
	}

	// MARK: - Caches

	/// Call to free up some memory. Should be done when the app is backgrounded, for instance.
	/// This does not empty *all* caches — just the ones that are empty-able.
	public func emptyCaches() {
		guard acceptsWork else { return }
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		articlesTable.emptyCaches()
	}

	// MARK: - Cleanup

	/// Calls the various clean-up functions. To be used only at startup.
	///
	/// This prevents the database from growing forever. If we didn’t do this:
	/// 1) The database would grow to an inordinate size, and
	/// 2) the app would become very slow.
	public func cleanupDatabaseAtStartup(subscribedToFeedIDs: Set<String>) {
		guard acceptsWork else { return }
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		if retentionStyle == .syncSystem {
			articlesTable.deleteOldArticles()
		}
		articlesTable.deleteArticlesNotInSubscribedToFeedIDs(subscribedToFeedIDs)
		articlesTable.deleteOldStatuses()
	}
}

// MARK: - Private

private extension ArticlesDatabase {

	static let tableCreationStatements = """
	CREATE TABLE if not EXISTS articles (articleID TEXT NOT NULL PRIMARY KEY, feedID TEXT NOT NULL, uniqueID TEXT NOT NULL, title TEXT, contentHTML TEXT, contentText TEXT, markdown TEXT, url TEXT, externalURL TEXT, summary TEXT, imageURL TEXT, bannerImageURL TEXT, datePublished DATE, dateModified DATE, searchRowID INTEGER, authors TEXT);

	CREATE TABLE if not EXISTS statuses (articleID TEXT NOT NULL PRIMARY KEY, read BOOL NOT NULL DEFAULT 0, starred BOOL NOT NULL DEFAULT 0, dateArrived DATE NOT NULL DEFAULT 0);

	CREATE INDEX if not EXISTS articles_feedID_datePublished_articleID on articles (feedID, datePublished, articleID);

	CREATE INDEX if not EXISTS statuses_starred_index on statuses (starred);

	CREATE VIRTUAL TABLE if not EXISTS search using fts4(title, body);

	CREATE TRIGGER if not EXISTS articles_after_delete_trigger_delete_search_text after delete on articles begin delete from search where rowid = OLD.searchRowID; end;
	"""

	func todayCutoffDate() -> Date {
		// 24 hours previous. This is used by the Today smart feed, which should not actually empty out at midnight.
		return Date(timeIntervalSinceNow: -(60 * 60 * 24)) // This does not need to be more precise.
	}
}

// MARK: - Articles Table (Private)

typealias UnreadCountDictionaryCompletionBlock = @Sendable (Result<UnreadCountDictionary, Error>) -> Void
typealias UpdateArticlesCompletionBlock = @Sendable (ArticleChanges) -> Void
typealias SingleUnreadCountCompletionBlock = @Sendable (Result<Int, Error>) -> Void
typealias ArticleSetResultBlock = @Sendable (Result<Set<Article>, Error>) -> Void
typealias ArticleIDsCompletionBlock = @Sendable (Result<Set<String>, Error>) -> Void
typealias ArticleIDsResultBlock = @Sendable (Result<Set<String>, Error>) -> Void

private extension ArticlesDatabase {

	func _fetchUnreadCounts(feedIDs: Set<String>, _ completion: @escaping UnreadCountDictionaryCompletionBlock) {
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		articlesTable.fetchUnreadCounts(feedIDs, completion)
	}

	func _fetchUnreadCount(feedIDs: Set<String>, since: Date, completion: @escaping SingleUnreadCountCompletionBlock) {
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		articlesTable.fetchUnreadCount(feedIDs, since, completion)
	}

	func _fetchStarredAndUnreadCount(feedIDs: Set<String>, completion: @escaping SingleUnreadCountCompletionBlock) {
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		articlesTable.fetchStarredAndUnreadCount(feedIDs, completion)
	}

	func _mark(articleIDs: Set<String>, statusKey: ArticleStatus.Key, flag: Bool, completion: @escaping ArticleIDsResultBlock) {
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		articlesTable.mark(articleIDs, statusKey, flag, completion)
	}

	func _markAndFetchNew(articleIDs: Set<String>, statusKey: ArticleStatus.Key, flag: Bool, completion: @escaping ArticleIDsCompletionBlock) {
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		articlesTable.markAndFetchNew(articleIDs, statusKey, flag, completion)
	}

	func _createStatusesIfNeeded(articleIDs: Set<String>, completion: @escaping DatabaseCompletionBlock) {
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		articlesTable.createStatusesIfNeeded(articleIDs, completion)
	}

	func _fetchArticlesAsync(feedID: String, _ completion: @escaping ArticleSetResultBlock) {
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		articlesTable.fetchArticlesAsync(feedID, completion)
	}

	func _fetchArticlesAsync(feedIDs: Set<String>, _ completion: @escaping ArticleSetResultBlock) {
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		articlesTable.fetchArticlesAsync(feedIDs, completion)
	}

	func _fetchArticlesAsync(articleIDs: Set<String>, _ completion: @escaping  ArticleSetResultBlock) {
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		articlesTable.fetchArticlesAsync(articleIDs: articleIDs, completion)
	}

	func _fetchUnreadArticlesAsync(feedIDs: Set<String>, limit: Int? = nil, _ completion: @escaping ArticleSetResultBlock) {
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		articlesTable.fetchUnreadArticlesAsync(feedIDs, limit, completion)
	}

	func _fetchTodayArticlesAsync(feedIDs: Set<String>, limit: Int? = nil, _ completion: @escaping ArticleSetResultBlock) {
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		articlesTable.fetchArticlesSinceAsync(feedIDs, todayCutoffDate(), limit, completion)
	}

	func _fetchedStarredArticlesAsync(feedIDs: Set<String>, limit: Int? = nil, _ completion: @escaping ArticleSetResultBlock) {
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		articlesTable.fetchStarredArticlesAsync(feedIDs, limit, completion)
	}

	func _fetchArticlesMatchingAsync(searchString: String, feedIDs: Set<String>, _ completion: @escaping ArticleSetResultBlock) {
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		articlesTable.fetchArticlesMatchingAsync(searchString, feedIDs, completion)
	}

	func _fetchArticlesMatchingWithArticleIDsAsync(searchString: String, articleIDs: Set<String>, _ completion: @escaping ArticleSetResultBlock) {
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		articlesTable.fetchArticlesMatchingWithArticleIDsAsync(searchString, articleIDs, completion)
	}

	func _update(parsedItems: Set<ParsedItem>, feedID: String, deleteOlder: Bool, completion: @escaping UpdateArticlesCompletionBlock) {
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		precondition(retentionStyle == .feedBased)
		articlesTable.update(parsedItems, feedID, deleteOlder, completion)
	}

	func _update(feedIDsAndItems: [String: Set<ParsedItem>], defaultRead: Bool, completion: @escaping UpdateArticlesCompletionBlock) {
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		precondition(retentionStyle == .syncSystem)
		articlesTable.update(feedIDsAndItems, defaultRead, completion)
	}

	func _delete(articleIDs: Set<String>, completion: @escaping @Sendable (Bool) -> Void) {
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		articlesTable.delete(articleIDs: articleIDs, completion: completion)
	}

	func _fetchUnreadArticleIDsAsync(completion: @escaping ArticleIDsCompletionBlock) {
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		articlesTable.fetchUnreadArticleIDsAsync(completion)
	}

	func _fetchStarredArticleIDsAsync(completion: @escaping ArticleIDsCompletionBlock) {
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		articlesTable.fetchStarredArticleIDsAsync(completion)
	}

	func _fetchArticleIDsForStatusesWithoutArticlesNewerThanCutoffDate(_ completion: @escaping ArticleIDsCompletionBlock) {
		Self.logger.debug("ArticlesDatabase: \(#function, privacy: .public) \(self.accountID, privacy: .public)")
		articlesTable.fetchArticleIDsForStatusesWithoutArticlesNewerThanCutoffDate(completion)
	}
}
