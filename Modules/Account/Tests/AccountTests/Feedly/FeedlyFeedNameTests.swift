//
//  FeedlyFeedNameTests.swift
//  AccountTests
//
//  Created by Brent Simmons on 8/15/26.
//

import Testing
@testable import Account

@MainActor struct FeedlyFeedNameTests {

	private let accountManager = TestAccountManager()

	@Test func missingTitleKeepsExistingName() async throws {
		try await accountManager.withAccount(type: .feedly) { account in
			let folder = try makeFolder(in: account)

			syncTitle("Feed One", folder: folder, account: account)
			syncTitle(nil, folder: folder, account: account)

			#expect(folder.existingFeed(withFeedID: "feed/1")?.name == "Feed One")
		}
	}

	@Test func emptyTitleKeepsExistingName() async throws {
		try await accountManager.withAccount(type: .feedly) { account in
			let folder = try makeFolder(in: account)

			syncTitle("Feed One", folder: folder, account: account)
			syncTitle("", folder: folder, account: account)

			#expect(folder.existingFeed(withFeedID: "feed/1")?.name == "Feed One")
		}
	}

	@Test func serverRenameLeavesEditedNameAlone() async throws {
		try await accountManager.withAccount(type: .feedly) { account in
			let folder = try makeFolder(in: account)

			syncTitle("Feed One", folder: folder, account: account)
			let feed = try #require(folder.existingFeed(withFeedID: "feed/1"))
			feed.editedName = "Edited Name"

			syncTitle("Renamed On Feedly", folder: folder, account: account)

			#expect(feed.editedName == "Edited Name")
			#expect(feed.name == "Renamed On Feedly")
			#expect(feed.nameForDisplay == "Edited Name")
		}
	}

	// MARK: - Helpers

	private func makeFolder(in account: Account) throws -> Folder {
		let folder = try #require(account.ensureFolder(with: "Folder"))
		folder.externalID = "folder/1"
		return folder
	}

	private func syncTitle(_ title: String?, folder: Folder, account: Account) {
		syncFeedsForCollectionFolders([
			([FeedlyFeed(id: "feed/1", title: title, updated: nil, website: nil)], folder)
		], in: account)
	}
}
