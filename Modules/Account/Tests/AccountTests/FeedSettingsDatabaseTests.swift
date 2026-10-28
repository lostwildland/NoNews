//
//  FeedSettingsDatabaseTests.swift
//  AccountTests
//
//  Created by Brent Simmons on 8/2/26.
//

import Foundation
import Testing
import Synchronization
import RSDatabase
@testable import Account

struct FeedSettingsDatabaseTests {
	@Test func admittedReadFinishesBeforeCloseWithoutHoldingAdmissionLock() async {
		let database = makeDatabase()
		database.ensureFeedExists("fixture", feedID: "fixture")
		let (started, startSignal) = AsyncStream<Void>.makeStream()
		let release = DispatchSemaphore(value: 0)
		#expect(database.enqueueForTesting { startSignal.yield(()); release.wait() })
		for await _ in started { break }
		let (submitted, signal) = AsyncStream<Void>.makeStream()
		database.readSubmittedForTesting.withLock { $0 = { signal.yield(()) } }
		let read = Task.detached { database.allRows()["fixture"]?.feedID == "fixture" }
		for await _ in submitted { break }
		database.beginClosing()
		#expect(!database.acceptsWork)
		let close = Task { await database.close() }
		release.signal()
		#expect(await read.value)
		#expect(await close.value)
		#expect(database.allRows().isEmpty && database.isEmpty)
	}

	@Test func feedIDColumnIsUpdatable() {
		let database = makeDatabase()
		let feedURL = "https://example.com/feed.xml"
		let canonicalFeedID = "feed/\(feedURL)"

		database.ensureFeedExists(feedURL, feedID: feedURL)
		database.setString(canonicalFeedID, for: feedURL, column: .feedID)

		#expect(database.allRows()[feedURL]?.feedID == canonicalFeedID)
	}

	@Test func ensureFeedExistsDoesNotReplaceFeedID() {
		let database = makeDatabase()
		let feedURL = "https://example.com/feed.xml"
		let canonicalFeedID = "feed/\(feedURL)"

		database.ensureFeedExists(feedURL, feedID: canonicalFeedID)
		database.ensureFeedExists(feedURL, feedID: feedURL)

		#expect(database.allRows()[feedURL]?.feedID == canonicalFeedID)
	}

	private func makeDatabase() -> FeedSettingsDatabase {
		FeedSettingsDatabase(databasePath: ":memory:")
	}
}
