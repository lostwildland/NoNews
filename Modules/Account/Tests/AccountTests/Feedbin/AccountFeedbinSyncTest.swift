//
//  AccountFeedbinSyncTest.swift
//  AccountTests
//
//  Created by Maurice Parker on 5/6/19.
//  Copyright © 2019 Ranchero Software, LLC. All rights reserved.
//

import XCTest
import RSWeb
@testable import Account

@MainActor final class AccountFeedbinSyncTest: XCTestCase {

	override func setUp() {
		TestingURLProtocol.reset()
	}

	func testDownloadSync() async throws {

		TestingURLProtocol.setResponse("tags.json", file: "JSON/tags_add.json")
		TestingURLProtocol.setResponse("subscriptions.json", file: "JSON/subscriptions_initial.json")
		try await TestAccountManager.shared.withAccount(type: .feedbin) { account in
			// Test initial folders
			try await account.refreshAll()

			XCTAssertEqual(224, account.flattenedFeeds().count)

			let daringFireball = account.idToFeedDictionary["1296379"]
			XCTAssertEqual("Daring Fireball", daringFireball!.name)
			XCTAssertEqual("https://daringfireball.net/feeds/json", daringFireball!.url)
			XCTAssertEqual("https://daringfireball.net/", daringFireball!.homePageURL)

			// Test Adding a Feed
			TestingURLProtocol.setResponse("subscriptions.json", file: "JSON/subscriptions_add.json")

			try await account.refreshAll()

			XCTAssertEqual(225, account.flattenedFeeds().count)

			let bPixels = account.idToFeedDictionary["1096623"]
			XCTAssertEqual("Beautiful Pixels", bPixels?.name)
			XCTAssertEqual("https://feedpress.me/beautifulpixels", bPixels?.url)
			XCTAssertEqual("https://beautifulpixels.com/", bPixels?.homePageURL)
		}
	}
}
