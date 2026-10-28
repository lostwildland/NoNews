//
//  ArticleUpdateTests.swift
//  ArticlesDatabase
//
//  Created by Brent Simmons on 9/16/26.
//

import Foundation
import Testing
import Articles
import RSParser
import ArticlesDatabase

/// Every refresh diffs incoming articles against stored ones and writes only
/// what changed. These tests cover the diff: a changed field persists, and an
/// unchanged article is not reported as updated.
///
/// The articles cache returns the incoming article rather than the stored row,
/// so each test empties it before checking what was actually written.
@MainActor @Suite final class ArticleUpdateTests {

	private let database: ArticlesDatabase
	private let feedID = "feed1"
	private let uniqueID = "1"

	init() {
		self.database = ArticlesDatabase(databaseFilePath: ":memory:", accountID: "test", retentionStyle: .feedBased)
	}

	@Test func identicalUpdateReportsNoChanges() async throws {
		let item = parsedItem(title: "Title", markdown: nil)
		let firstChanges = await database.updateAsync(parsedItems: [item], feedID: feedID, deleteOlder: false)
		#expect(firstChanges.new?.count == 1)

		database.emptyCaches()
		let secondChanges = await database.updateAsync(parsedItems: [item], feedID: feedID, deleteOlder: false)
		#expect(secondChanges.new == nil)
		#expect(secondChanges.updated == nil)
	}

	@Test func markdownChangePersists() async throws {
		let original = parsedItem(title: "Title", markdown: "one")
		_ = await database.updateAsync(parsedItems: [original], feedID: feedID, deleteOlder: false)

		let edited = parsedItem(title: "Title", markdown: "two")
		let changes = await database.updateAsync(parsedItems: [edited], feedID: feedID, deleteOlder: false)
		#expect(changes.updated?.count == 1)

		database.emptyCaches()
		let fetched = try await database.fetchArticlesAsync(feedID: feedID).first
		#expect(fetched?.markdown == "two")
	}

	@Test func deferredCommitFailureLeavesArticleAndStatusUnchanged() async throws {
		let initial = parsedItem(title: "Before", markdown: nil)
		#expect((await database.updateAsync(parsedItems: [initial], feedID: feedID, deleteOlder: false)).error == nil)
		let article = try #require(try await database.fetchArticlesAsync(feedID: feedID).first)
		let beforeRead = article.status.read
		#expect(database.executeSQLForTesting("PRAGMA foreign_keys=ON; CREATE TABLE fixture_parent (id INTEGER PRIMARY KEY); CREATE TABLE fixture_child (id INTEGER REFERENCES fixture_parent(id) DEFERRABLE INITIALLY DEFERRED); CREATE TRIGGER fixture_article AFTER UPDATE ON articles BEGIN INSERT INTO fixture_child VALUES (1); END; CREATE TRIGGER fixture_status AFTER UPDATE ON statuses BEGIN INSERT INTO fixture_child VALUES (1); END;"))
		await #expect(throws: (any Error).self) { _ = try await database.markAsync(articleIDs: [article.articleID], statusKey: .read, flag: !beforeRead) }
		#expect(article.status.read == beforeRead)
		let failed = await database.updateAsync(parsedItems: [parsedItem(title: "After", markdown: nil)], feedID: feedID, deleteOlder: false)
		#expect(failed.error != nil)
		#expect(try await database.fetchArticlesAsync(feedID: feedID).first?.title == "Before")
		#expect(database.executeSQLForTesting("DROP TRIGGER fixture_article; DROP TRIGGER fixture_status; DROP TABLE fixture_child; DROP TABLE fixture_parent;"))
		#expect(try await database.markAsync(articleIDs: [article.articleID], statusKey: .read, flag: !beforeRead) == [article.articleID])
		#expect((await database.updateAsync(parsedItems: [parsedItem(title: "After", markdown: nil)], feedID: feedID, deleteOlder: false)).error == nil)
		#expect(try await database.fetchArticlesAsync(feedID: feedID).first?.title == "After")
		#expect(await database.close())
	}

	@Test func failedSearchIndexWriteRollsBackArticleAndCanRetry() async throws {
		#expect(database.executeSQLForTesting("DROP TABLE search;"))
		let item = parsedItem(title: "Fixture", markdown: nil)
		let failed = await database.updateAsync(parsedItems: [item], feedID: feedID, deleteOlder: false)
		#expect(failed.error != nil)
		#expect(try await database.fetchArticlesAsync(feedID: feedID).isEmpty)
		#expect(database.executeSQLForTesting("CREATE VIRTUAL TABLE search USING fts4(title, body);"))
		let retry = await database.updateAsync(parsedItems: [item], feedID: feedID, deleteOlder: false)
		#expect(retry.error == nil && retry.new?.count == 1)
		#expect(await database.close())
	}

	@Test func clearedFieldStopsReportingAsUpdated() async throws {
		let withTitle = parsedItem(title: "Title", markdown: nil)
		_ = await database.updateAsync(parsedItems: [withTitle], feedID: feedID, deleteOlder: false)

		let withoutTitle = parsedItem(title: nil, markdown: nil)
		let clearingChanges = await database.updateAsync(parsedItems: [withoutTitle], feedID: feedID, deleteOlder: false)
		#expect(clearingChanges.updated?.count == 1)

		database.emptyCaches()
		let fetched = try await database.fetchArticlesAsync(feedID: feedID).first
		#expect(fetched?.title == nil)

		database.emptyCaches()
		let repeatChanges = await database.updateAsync(parsedItems: [withoutTitle], feedID: feedID, deleteOlder: false)
		#expect(repeatChanges.updated == nil)
	}

	@Test func equalityComparesMarkdown() {
		let one = article(markdown: "one")
		let two = article(markdown: "two")
		#expect(one != two)
		#expect(one == article(markdown: "one"))
	}
}

// MARK: - Helpers

private extension ArticleUpdateTests {

	func parsedItem(title: String?, markdown: String?) -> ParsedItem {
		ParsedItem(syncServiceID: nil, uniqueID: uniqueID, feedURL: feedID, url: "https://example.com/\(uniqueID)", externalURL: nil, title: title, language: nil, contentHTML: "<p>Test</p>", contentText: nil, markdown: markdown, summary: nil, imageURL: nil, bannerImageURL: nil, datePublished: Date(timeIntervalSince1970: 0), dateModified: nil, authors: nil, tags: nil, attachments: nil)
	}

	func article(markdown: String?) -> Article {
		let status = ArticleStatus(articleID: "article1", read: false, starred: false, dateArrived: Date(timeIntervalSince1970: 0))
		return Article(accountID: "test", articleID: "article1", feedID: feedID, uniqueID: uniqueID, title: "Title", contentHTML: "<p>Test</p>", contentText: nil, markdown: markdown, url: nil, externalURL: nil, summary: nil, imageURL: nil, datePublished: nil, dateModified: nil, authors: nil, status: status)
	}
}
