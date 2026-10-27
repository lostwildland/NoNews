//
//  FeedSettingsDatabase.swift
//  Account
//
//  Created by Brent Simmons on 3/6/26.
//

import Foundation
import Synchronization
import RSCore
import os
import RSDatabase
import RSDatabaseObjC
import RSWeb
import Articles

final class FeedSettingsDatabase: Sendable {
	enum Column: String {
		case feedID
		case homePageURL
		case iconURL
		case faviconURL
		case editedName
		case contentHash
		case newArticleNotificationsEnabled
		case readerViewAlwaysEnabled
		case authors
		case conditionalGetInfoLastModified
		case conditionalGetInfoEtag
		case conditionalGetInfoDate
		case cacheControlInfoDateCreated
		case cacheControlInfoMaxAge
		case externalID
		case folderRelationship
		case lastCheckDate
		case lastResponseCode
	}

	struct Row {
		let feedID: String
		let homePageURL: String?
		let iconURL: String?
		let faviconURL: String?
		let editedName: String?
		let contentHash: String?
		let newArticleNotificationsEnabled: Bool
		let readerViewAlwaysEnabled: Bool
		let authors: Set<Author>?
		let conditionalGetInfo: HTTPConditionalGetInfo?
		let conditionalGetInfoDate: Date?
		let cacheControlInfo: CacheControlInfo?
		let externalID: String?
		let folderRelationship: [String: String]?
		let lastCheckDate: Date?
		let lastResponseCode: Int?
	}

	let databasePath: String
	private let accountID: String?
	private let closing = Mutex((closing: false, sealed: false))

	var acceptsWork: Bool { closing.withLock { !$0.sealed && (!$0.closing || (accountID != nil && DatabaseWork.current?.isActive == true && DatabaseWork.current?.accountID == accountID)) } }
	func beginClosing() { closing.withLock { $0.closing = true } }

	@discardableResult private func submit(_ work: @escaping @Sendable () -> Void) -> Bool {
		closing.withLock { closing in
			guard !closing.sealed && (!closing.closing || (accountID != nil && DatabaseWork.current?.isActive == true && DatabaseWork.current?.accountID == accountID)) else { return false }
			serialDispatchQueue.async(execute: work)
			return true
		}
	}

	nonisolated(unsafe) private let database: FMDatabase // Used on serial dispatch queue only
	private let serialDispatchQueue: DispatchQueue
	private static let logger = Logger(subsystem: Logger.nnwSubsystem, category: "FeedSettingsDatabase")

	#if DEBUG
	func withDatabaseForTesting<T>(_ body: (FMDatabase) -> T) -> T {
		serialDispatchQueue.sync { body(database) }
	}
	#endif

	init(databasePath: String, accountID: String? = nil) {
		self.accountID = accountID
		self.databasePath = databasePath
		self.serialDispatchQueue = DispatchQueue(label: "FeedSettingsDatabase")
		self.database = FMDatabase.openAndSetUpDatabase(path: databasePath)
		serialDispatchQueue.sync { [database] in
			database.runCreateStatements(Self.tableCreationStatements)
			if !database.columnExists("lastResponseCode", inTableWithName: "feedSettings") {
				database.executeStatements("ALTER TABLE feedSettings ADD COLUMN lastResponseCode INTEGER;")
			}
		}
		vacuumIfNeeded()
	}

	func vacuum() async {
		await withCheckedContinuation { continuation in
			if !submit({
				self.database.vacuum()
				continuation.resume()
			}) { continuation.resume() }
		}
	}

	func close() async -> Bool {
		beginClosing()
		return await withCheckedContinuation { continuation in
			closing.withLock { state in
				state.sealed = true
				serialDispatchQueue.async {
					continuation.resume(returning: self.database.close())
				}
			}
		}
	}

	@discardableResult func vacuumIfNeeded() -> Bool {
		return submit {
			self.database.vacuumIfNeeded()
		}
	}

	var isEmpty: Bool {
		return closing.withLock { closing in
			guard !closing.sealed && (!closing.closing || (accountID != nil && DatabaseWork.current?.isActive == true && DatabaseWork.current?.accountID == accountID)) else { return true }
			return serialDispatchQueue.sync {
			guard let resultSet = self.database.executeQuery("SELECT 1 FROM feedSettings LIMIT 1;", withArgumentsIn: []) else {
				return true
			}
			defer {
				resultSet.close()
			}
			return !resultSet.next()
			}
		}
	}

	// MARK: - Feed Existence

	@discardableResult func ensureFeedExists(_ feedURL: String, feedID: String) -> Bool {
		return submit {
			self.database.executeUpdate("INSERT OR IGNORE INTO feedSettings (feedURL, feedID) VALUES (?, ?);", withArgumentsIn: [feedURL, feedID])
		}
	}

	// MARK: - Insert Row

	@discardableResult func insertRow(_ feedURL: String, _ columnValues: [Column: Any]) -> Bool {
		var dictionary = DatabaseDictionary()
		dictionary["feedURL"] = feedURL
		for (column, value) in columnValues {
			dictionary[column.rawValue] = value
		}
		nonisolated(unsafe) let capturedDictionary = dictionary
		return submit {
			self.database.insertRow(capturedDictionary, insertType: .orReplace, tableName: "feedSettings")
		}
	}

	// MARK: - Fetch Rows

	func allRows() -> [String: Row] {
		return closing.withLock { closing in
			guard !closing.sealed && (!closing.closing || (accountID != nil && DatabaseWork.current?.isActive == true && DatabaseWork.current?.accountID == accountID)) else { return [:] }
			return serialDispatchQueue.sync {
			guard let resultSet = self.database.executeQuery("SELECT * FROM feedSettings;", withArgumentsIn: []) else {
				return [:]
			}
			defer {
				resultSet.close()
			}

			var rows = [String: Row]()
			while resultSet.next() {
				if let feedURL = resultSet.swiftString(forColumn: "feedURL") {
					rows[feedURL] = self.row(from: resultSet)
				}
			}
			return rows
			}
		}
	}

	// MARK: - String

	@discardableResult func setString(_ value: String?, for feedURL: String, column: Column) -> Bool {
		let name = column.rawValue
		return submit {
			if let value {
				self.database.executeUpdate("UPDATE feedSettings SET \(name) = ? WHERE feedURL = ?;", withArgumentsIn: [value, feedURL])
			} else {
				self.database.executeUpdate("UPDATE feedSettings SET \(name) = NULL WHERE feedURL = ?;", withArgumentsIn: [feedURL])
			}
		}
	}

	// MARK: - Bool

	@discardableResult func setBool(_ value: Bool, for feedURL: String, column: Column) -> Bool {
		let name = column.rawValue
		return submit {
			self.database.executeUpdate("UPDATE feedSettings SET \(name) = ? WHERE feedURL = ?;", withArgumentsIn: [value, feedURL])
		}
	}

	// MARK: - Int

	@discardableResult func setInt(_ value: Int?, for feedURL: String, column: Column) -> Bool {
		let name = column.rawValue
		return submit {
			if let value {
				self.database.executeUpdate("UPDATE feedSettings SET \(name) = ? WHERE feedURL = ?;", withArgumentsIn: [value, feedURL])
			} else {
				self.database.executeUpdate("UPDATE feedSettings SET \(name) = NULL WHERE feedURL = ?;", withArgumentsIn: [feedURL])
			}
		}
	}

	// MARK: - Date

	@discardableResult func setDate(_ value: Date?, for feedURL: String, column: Column) -> Bool {
		let name = column.rawValue
		return submit {
			if let value {
				self.database.executeUpdate("UPDATE feedSettings SET \(name) = ? WHERE feedURL = ?;", withArgumentsIn: [value.timeIntervalSinceReferenceDate, feedURL])
			} else {
				self.database.executeUpdate("UPDATE feedSettings SET \(name) = NULL WHERE feedURL = ?;", withArgumentsIn: [feedURL])
			}
		}
	}

	// MARK: - Compound Types

	@discardableResult func setConditionalGetInfo(_ info: HTTPConditionalGetInfo?, for feedURL: String) -> Bool {
		return submit {
			if let info {
				self.database.executeUpdate("UPDATE feedSettings SET conditionalGetInfoLastModified = ?, conditionalGetInfoEtag = ? WHERE feedURL = ?;", withArgumentsIn: [info.lastModified as Any, info.etag as Any, feedURL])
			} else {
				self.database.executeUpdate("UPDATE feedSettings SET conditionalGetInfoLastModified = NULL, conditionalGetInfoEtag = NULL WHERE feedURL = ?;", withArgumentsIn: [feedURL])
			}
		}
	}

	@discardableResult func setCacheControlInfo(_ info: CacheControlInfo?, for feedURL: String) -> Bool {
		return submit {
			if let info {
				self.database.executeUpdate("UPDATE feedSettings SET cacheControlInfoDateCreated = ?, cacheControlInfoMaxAge = ? WHERE feedURL = ?;", withArgumentsIn: [info.dateCreated.timeIntervalSinceReferenceDate, info.maxAge, feedURL])
			} else {
				self.database.executeUpdate("UPDATE feedSettings SET cacheControlInfoDateCreated = NULL, cacheControlInfoMaxAge = NULL WHERE feedURL = ?;", withArgumentsIn: [feedURL])
			}
		}
	}

	@discardableResult func setAuthors(_ authors: Set<Author>?, for feedURL: String) -> Bool {
		return submit {
			if let authors {
				let jsonString = authors.json()
				self.database.executeUpdate("UPDATE feedSettings SET authors = ? WHERE feedURL = ?;", withArgumentsIn: [jsonString as Any, feedURL])
			} else {
				self.database.executeUpdate("UPDATE feedSettings SET authors = NULL WHERE feedURL = ?;", withArgumentsIn: [feedURL])
			}
		}
	}

	@discardableResult func setFolderRelationship(_ relationship: [String: String]?, for feedURL: String) -> Bool {
		return submit {
			if let relationship {
				if let data = try? JSONSerialization.data(withJSONObject: relationship), let jsonString = String(data: data, encoding: .utf8) {
					self.database.executeUpdate("UPDATE feedSettings SET folderRelationship = ? WHERE feedURL = ?;", withArgumentsIn: [jsonString, feedURL])
				}
			} else {
				self.database.executeUpdate("UPDATE feedSettings SET folderRelationship = NULL WHERE feedURL = ?;", withArgumentsIn: [feedURL])
			}
		}
	}

	// MARK: - Deletion

	@discardableResult func deleteSettings(for feedURL: String) -> Bool {
		return submit {
			self.database.executeUpdate("DELETE FROM feedSettings WHERE feedURL = ?;", withArgumentsIn: [feedURL])
		}
	}

	// MARK: - Cleanup on launch

	@discardableResult func deleteSettingsForFeedsNotIn(_ feedURLs: Set<String>) -> Bool {
		guard !feedURLs.isEmpty else {
			return true
		}

		let feedURLsArray = Array(feedURLs)
		return submit {
			let placeholders = NSString.rs_SQLValueList(withPlaceholders: UInt(feedURLsArray.count))
			let sql = "DELETE FROM feedSettings WHERE feedURL NOT IN \(placeholders);"
			self.database.executeUpdate(sql, withArgumentsIn: feedURLsArray)

			#if DEBUG
			let numberOfRowChanges: Int32 = self.database.changes()
			if numberOfRowChanges > 0 {
				Self.logger.info("FeedSettingsDatabase: deleteSettingsForFeedsNotIn: deleted \(numberOfRowChanges) orphaned feed settings")
			}
			#endif
		}
	}
}

// MARK: - Private

private extension FeedSettingsDatabase {

	static let tableCreationStatements = """
	CREATE TABLE IF NOT EXISTS feedSettings (feedURL TEXT PRIMARY KEY, feedID TEXT NOT NULL DEFAULT '', homePageURL TEXT, iconURL TEXT, faviconURL TEXT, editedName TEXT, contentHash TEXT, newArticleNotificationsEnabled INTEGER NOT NULL DEFAULT 0, readerViewAlwaysEnabled INTEGER NOT NULL DEFAULT 0, authors TEXT, conditionalGetInfoLastModified TEXT, conditionalGetInfoEtag TEXT, conditionalGetInfoDate REAL, cacheControlInfoDateCreated REAL, cacheControlInfoMaxAge REAL, externalID TEXT, folderRelationship TEXT, lastCheckDate REAL, lastResponseCode INTEGER);
	"""

	func row(from resultSet: FMResultSet) -> Row {
		let lastModified = resultSet.swiftString(forColumn: Column.conditionalGetInfoLastModified.rawValue)
		let etag = resultSet.swiftString(forColumn: Column.conditionalGetInfoEtag.rawValue)

		var conditionalGetInfoDate: Date?
		if !resultSet.columnIsNull(Column.conditionalGetInfoDate.rawValue) {
			conditionalGetInfoDate = Date(timeIntervalSinceReferenceDate: resultSet.double(forColumn: Column.conditionalGetInfoDate.rawValue))
		}

		var cacheControlInfo: CacheControlInfo?
		if !resultSet.columnIsNull(Column.cacheControlInfoDateCreated.rawValue) && !resultSet.columnIsNull(Column.cacheControlInfoMaxAge.rawValue) {
			let dateCreated = Date(timeIntervalSinceReferenceDate: resultSet.double(forColumn: Column.cacheControlInfoDateCreated.rawValue))
			let maxAge = resultSet.double(forColumn: Column.cacheControlInfoMaxAge.rawValue)
			cacheControlInfo = CacheControlInfo(dateCreated: dateCreated, maxAge: maxAge)
		}

		var authors: Set<Author>?
		if let authorsData = resultSet.data(forColumn: Column.authors.rawValue) {
			authors = Author.authorsWithJSON(authorsData)
		}

		var folderRelationship: [String: String]?
		if let folderData = resultSet.data(forColumn: Column.folderRelationship.rawValue) {
			folderRelationship = try? JSONSerialization.jsonObject(with: folderData) as? [String: String]
		}

		var lastCheckDate: Date?
		if !resultSet.columnIsNull(Column.lastCheckDate.rawValue) {
			lastCheckDate = Date(timeIntervalSinceReferenceDate: resultSet.double(forColumn: Column.lastCheckDate.rawValue))
		}

		var lastResponseCode: Int?
		if !resultSet.columnIsNull(Column.lastResponseCode.rawValue) {
			lastResponseCode = Int(resultSet.int(forColumn: Column.lastResponseCode.rawValue))
		}

		return Row(
			feedID: resultSet.swiftString(forColumn: Column.feedID.rawValue) ?? "",
			homePageURL: resultSet.swiftString(forColumn: Column.homePageURL.rawValue),
			iconURL: resultSet.swiftString(forColumn: Column.iconURL.rawValue),
			faviconURL: resultSet.swiftString(forColumn: Column.faviconURL.rawValue),
			editedName: resultSet.swiftString(forColumn: Column.editedName.rawValue),
			contentHash: resultSet.swiftString(forColumn: Column.contentHash.rawValue),
			newArticleNotificationsEnabled: resultSet.bool(forColumn: Column.newArticleNotificationsEnabled.rawValue),
			readerViewAlwaysEnabled: resultSet.bool(forColumn: Column.readerViewAlwaysEnabled.rawValue),
			authors: authors,
			conditionalGetInfo: HTTPConditionalGetInfo(lastModified: lastModified, etag: etag),
			conditionalGetInfoDate: conditionalGetInfoDate,
			cacheControlInfo: cacheControlInfo,
			externalID: resultSet.swiftString(forColumn: Column.externalID.rawValue),
			folderRelationship: folderRelationship,
			lastCheckDate: lastCheckDate,
			lastResponseCode: lastResponseCode
		)
	}
}
