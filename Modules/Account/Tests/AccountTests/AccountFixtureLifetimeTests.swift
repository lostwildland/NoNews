import Darwin
import Foundation
import SQLite3
import Testing
import RSWeb
import SyncDatabase
import Articles
import Synchronization
import RSCore
@testable import Account

private final class GatedRefreshURLProtocol: URLProtocol, @unchecked Sendable {
	private final class Transfer: @unchecked Sendable {
		let value: GatedRefreshURLProtocol
		init(_ value: GatedRefreshURLProtocol) { self.value = value }
	}
	@MainActor static var onRequest: (() async -> Void)?
	override class func canInit(with request: URLRequest) -> Bool { true }
	override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
	override func startLoading() {
		let transfer = Transfer(self)
		Task { @MainActor in
			let instance = transfer.value
			await Self.onRequest?()
			guard let url = instance.request.url else { return }
			let response = HTTPURLResponse(url: url, statusCode: 200, httpVersion: "HTTP/1.1", headerFields: ["ETag": "fixture-etag"])!
			let xml = """
			<?xml version="1.0"?><rss version="2.0"><channel><title>Refreshed fixture</title><link>https://fixture.invalid/</link><description>Fixture</description><item><title>Refresh article</title><guid>refresh-article</guid><link>https://fixture.invalid/article</link></item></channel></rss>
			"""
			instance.client?.urlProtocol(instance, didReceive: response, cacheStoragePolicy: .notAllowed)
			instance.client?.urlProtocol(instance, didLoad: Data(xml.utf8))
			instance.client?.urlProtocolDidFinishLoading(instance)
		}
	}
	override func stopLoading() {}
}

@Suite(.isolatedWebserviceResponses, .serialized) @MainActor struct AccountFixtureLifetimeTests {
	private enum FixtureError: Error, Equatable { case expected }
	private final class NotificationCounter: Sendable { let count = Mutex(0) }

	@Test func immediateRefreshDrainsOwnedDownloadAfterCloseBegins() async throws {
		let manager = TestAccountManager()
		let account = manager.createAccount(type: .onMyMac)
		let delegate = try #require(account.delegate as? LocalAccountDelegate)
		delegate.refreshProtocolClassesForTesting = [GatedRefreshURLProtocol.self]
		let path = account.dataFolder
		let feed = account.createFeed(with: "Before", url: "https://fixture.invalid/refresh.xml", feedID: "refresh", homePageURL: nil)
		account.addFeedToTreeAtTopLevel(feed)
		account.saveIfNeeded()
		let (requested, requestSignal) = AsyncStream<Void>.makeStream()
		let (release, releaseSignal) = AsyncStream<Void>.makeStream()
		let (closing, closingSignal) = AsyncStream<Void>.makeStream()
		account.onFixtureClosingForTesting = { closingSignal.yield(()) }
		GatedRefreshURLProtocol.onRequest = {
			requestSignal.yield(())
			for await _ in release { break }
		}
		defer { GatedRefreshURLProtocol.onRequest = nil }
		let releaseTask = Task { @MainActor in
			for await _ in closing { break }
			for await _ in requested { break }
			releaseSignal.yield(())
		}
		account.triggerRefreshAll()
		let closed = await account.closeForFixtureRemoval()
		requestSignal.finish()
		releaseSignal.finish()
		await releaseTask.value
		#expect(closed)
		#expect(feed.lastResponseCode == 200)
		#expect(feed.conditionalGetInfo?.etag == "fixture-etag")
		#expect(feed.contentHash != nil)
		#expect(try stringValue(in: path + "/DB.sqlite3", sql: "SELECT title FROM articles WHERE title = 'Refresh article'") == "Refresh article")
		#expect(try stringValue(in: path + "/FeedSettings.db", sql: "SELECT conditionalGetInfoEtag FROM feedSettings WHERE feedID = 'refresh'") == "fixture-etag")
		let opml = try String(contentsOfFile: path + "/Subscriptions.opml", encoding: .utf8)
		#expect(opml.contains("Refreshed fixture"))
		try await manager.deleteAccount(account)
	}

	@Test func completionUsesCallerAdmissionInsteadOfProviderAdmission() async throws {
		let manager = TestAccountManager()
		let account = manager.createAccount(type: .onMyMac)
		let folder = try #require(account.ensureFolder(with: "Original"))
		let feed = account.createFeed(with: "Fixture", url: "https://fixture.invalid/completion", feedID: "completion", homePageURL: nil)
		let (closing, closingSignal) = AsyncStream<Void>.makeStream()
		let (release, releaseSignal) = AsyncStream<Void>.makeStream()
		account.onFixtureClosingForTesting = { closingSignal.yield(()) }
		var externalCalls = 0
		var inheritedCalls = 0
		var rejectedCalls = 0
		var leakedChange = false
		account.addFeed(feed, to: folder) { result in
			externalCalls += 1
			if case .failure(let error) = result { Issue.record("Accepted callback failed: \(error)") }
			folder.name = "Rejected"
			leakedChange = folder.name == "Rejected"
			account.removeFolder(folder) { result in
				rejectedCalls += 1
				if case .failure(let error) = result { #expect(error is CancellationError) } else { Issue.record("Unrelated callback work succeeded") }
			}
		}
		account.startBackground {
			for await _ in release { break }
			await withCheckedContinuation { continuation in
				account.addFeed(feed, to: folder) { result in
					inheritedCalls += 1
					if case .failure(let error) = result { Issue.record("Inherited callback failed: \(error)") }
					folder.name = "Inherited"
					continuation.resume()
				}
			}
		}
		let releaser = Task { @MainActor in
			for await _ in closing { break }
			releaseSignal.yield(())
		}
		#expect(await account.closeForFixtureRemoval())
		await releaser.value
		#expect(externalCalls == 1 && inheritedCalls == 1 && rejectedCalls == 1)
		#expect(!leakedChange)
		#expect(folder.name == "Inherited")
		let opml = try String(contentsOfFile: account.dataFolder + "/Subscriptions.opml", encoding: .utf8)
		#expect(opml.contains("Inherited") && !opml.contains("Rejected"))
		try await manager.deleteAccount(account)
	}

	@Test func retainedFeedRejectsSettingsWhenAccountIsReleasedWithoutClose() async throws {
		let manager = TestAccountManager()
		var account: Account? = manager.createAccount(type: .onMyMac)
		let path = try #require(account).dataFolder
		let url = "https://fixture.invalid/released-settings.xml"
		let feed = try #require(account).createFeed(with: "Original", url: url, feedID: "released-settings", homePageURL: "https://fixture.invalid/original")
		let database = try #require(account).feedSettingsDatabaseForTesting
		let articles = try #require(account).database
		let identities = try [identity(path + "/FeedSettings.db"), identity(path + "/DB.sqlite3")]
		feed.editedName = "Open"
		feed.homePageURL = "https://fixture.invalid/home"
		feed.conditionalGetInfo = HTTPConditionalGetInfo(lastModified: nil, etag: "original-etag")
		feed.newArticleNotificationsEnabled = true
		feed.folderRelationship = ["Folder": "original-id"]
		try #require(account).startBackground { feed.editedName = "Admitted" }
		await account?.waitForFixtureBackgroundWorkForTesting()
		#expect(feed.editedName == "Admitted")
		let before = try #require(database.allRows()[url])
		#expect(before.editedName == "Admitted")
		#expect(before.homePageURL == "https://fixture.invalid/home")
		#expect(before.conditionalGetInfo?.etag == "original-etag")
		#expect(before.newArticleNotificationsEnabled)
		#expect(before.folderRelationship == ["Folder": "original-id"])
		weak var owner = account
		account = nil
		if let owner {
			Issue.record("Account remained alive after its background work finished")
			try await manager.deleteAccount(owner)
			return
		}
		#expect(feed.account == nil)
		let changes = NotificationCounter()
		let settingsObserver = NotificationCenter.default.addObserver(forName: .feedSettingDidChange, object: feed, queue: nil) { _ in
			changes.count.withLock { $0 += 1 }
		}
		let displayObserver = NotificationCenter.default.addObserver(forName: .DisplayNameDidChange, object: feed, queue: nil) { _ in
			changes.count.withLock { $0 += 1 }
		}
		feed.editedName = "Rejected"
		feed.homePageURL = "https://fixture.invalid/rejected"
		feed.conditionalGetInfo = HTTPConditionalGetInfo(lastModified: nil, etag: "rejected-etag")
		feed.newArticleNotificationsEnabled = false
		feed.folderRelationship = ["Folder": "rejected-id"]
		#expect(feed.editedName == "Admitted")
		#expect(feed.homePageURL == "https://fixture.invalid/home")
		#expect(feed.conditionalGetInfo?.etag == "original-etag")
		#expect(feed.newArticleNotificationsEnabled)
		#expect(feed.folderRelationship == ["Folder": "original-id"])
		#expect(changes.count.withLock { $0 } == 0)
		let after = try #require(database.allRows()[url])
		#expect(after.editedName == before.editedName && after.homePageURL == before.homePageURL)
		#expect(after.conditionalGetInfo == before.conditionalGetInfo && after.conditionalGetInfoDate == before.conditionalGetInfoDate)
		#expect(after.newArticleNotificationsEnabled == before.newArticleNotificationsEnabled && after.folderRelationship == before.folderRelationship)
		NotificationCenter.default.removeObserver(settingsObserver)
		NotificationCenter.default.removeObserver(displayObserver)
		let articlesClosed = await articles.close()
		let settingsClosed = await database.close()
		guard articlesClosed && settingsClosed && !identities.contains(where: hasOpenFile) else {
			Issue.record("Fixture databases did not close")
			return
		}
		try FileManager.default.removeItem(atPath: path)
	}

	@Test func callbacksSubmittedBeforeCloseFinishAndPersist() async throws {
		let manager = TestAccountManager()
		let account = manager.createAccount(type: .onMyMac)
		let path = account.dataFolder
		let from = try #require(account.ensureFolder(with: "From"))
		let to = try #require(account.ensureFolder(with: "To"))
		let renameFolder = try #require(account.ensureFolder(with: "Rename"))
		let removedFolder = try #require(account.ensureFolder(with: "Remove"))
		let restoredFolder = Folder(account: account, name: "Restore")
		let feed = account.createFeed(with: "Feed", url: "https://fixture.invalid/callback-feed", feedID: "callback-feed", homePageURL: nil)
		let moved = account.createFeed(with: "Moved", url: "https://fixture.invalid/callback-move", feedID: "callback-move", homePageURL: nil)
		let removed = account.createFeed(with: "Removed", url: "https://fixture.invalid/callback-remove", feedID: "callback-remove", homePageURL: nil)
		let restored = account.createFeed(with: "Restored", url: "https://fixture.invalid/callback-restore", feedID: "callback-restore", homePageURL: nil)
		from.addFeedToTreeAtTopLevel(moved)
		from.addFeedToTreeAtTopLevel(removed)
		let url = "https://fixture.invalid/callback-created.xml"
		let xml = """
		<?xml version="1.0"?><rss version="2.0"><channel><title>Fixture</title><link>https://fixture.invalid/</link><description>Fixture</description><item><title>Callback article</title><guid>callback-article</guid><link>https://fixture.invalid/item</link></item></channel></rss>
		"""
		TestingURLProtocol.$currentTestID.withValue(nil) {
			TestingURLProtocol.setResponse(.init(data: Data(xml.utf8)), forURLContaining: url)
		}
		let importURL = URL(fileURLWithPath: path + "/import.opml")
		try "<opml version=\"2.0\"><body><outline text=\"Imported\" xmlUrl=\"https://fixture.invalid/imported.xml\"/></body></opml>".write(to: importURL, atomically: true, encoding: .utf8)
		var results = [Result<Void, Error>]()
		var creation: Result<Feed, Error>?
		account.addFeed(feed, to: from) { results.append($0) }
		account.moveFeed(moved, from: from, to: to) { results.append($0) }
		account.removeFeed(removed, from: from) { results.append($0) }
		account.restoreFeed(restored, container: to) { results.append($0) }
		account.removeFolder(removedFolder) { results.append($0) }
		account.restoreFolder(restoredFolder) { results.append($0) }
		feed.rename(to: "Accepted feed") { results.append($0) }
		renameFolder.rename(to: "Accepted folder") { results.append($0) }
		account.importOPML(importURL) { results.append($0) }
		account.createFeed(url: url, name: nil, container: to, validateFeed: true) { creation = $0 }
		#expect(results.isEmpty)
		if case .some = creation { Issue.record("Creation callback ran before close") }
		#expect(await account.closeForFixtureRemoval())
		#expect(results.count == 9)
		for result in results { if case .failure(let error) = result { Issue.record("Accepted callback failed: \(error)") } }
		_ = try #require(creation).get()
		#expect(from.topLevelFeeds.contains(feed))
		#expect(to.topLevelFeeds.contains(moved))
		#expect(!from.topLevelFeeds.contains(removed) && to.topLevelFeeds.contains(restored))
		#expect(renameFolder.name == "Accepted folder")
		#expect(account.folders?.contains(removedFolder) == false)
		#expect(account.folders?.contains(restoredFolder) == true)
		#expect(try stringValue(in: path + "/DB.sqlite3", sql: "SELECT title FROM articles WHERE title = 'Callback article'") == "Callback article")
		let opml = try String(contentsOfFile: path + "/Subscriptions.opml", encoding: .utf8)
		#expect(opml.contains("Accepted folder") && opml.contains(url) && opml.contains("imported.xml"))
		var rejected = [Result<Void, Error>]()
		account.removeFeed(feed, from: from) { rejected.append($0) }
		account.restoreFeed(feed, container: to) { rejected.append($0) }
		account.addFeed(feed, to: to) { rejected.append($0) }
		account.moveFeed(feed, from: from, to: to) { rejected.append($0) }
		account.removeFolder(renameFolder) { rejected.append($0) }
		account.restoreFolder(removedFolder) { rejected.append($0) }
		account.importOPML(importURL) { rejected.append($0) }
		feed.rename(to: "Rejected") { rejected.append($0) }
		renameFolder.rename(to: "Rejected") { rejected.append($0) }
		var rejectedCreation: Result<Feed, Error>?
		account.createFeed(url: url, name: nil, container: to, validateFeed: true) { rejectedCreation = $0 }
		#expect(rejected.count == 9)
		for result in rejected { if case .failure(let error) = result { #expect(error is CancellationError) } else { Issue.record("Closed callback succeeded") } }
		if case .failure(let error) = try #require(rejectedCreation) { #expect(error is CancellationError) } else { Issue.record("Closed creation succeeded") }
		#expect(from.topLevelFeeds.contains(feed) && renameFolder.name == "Accepted folder")
		try await manager.deleteAccount(account)
	}

	@Test func failedOPMLFlushKeepsDirtySubscriptionsForRetry() async throws {
		let manager = TestAccountManager()
		let account = manager.createAccount(type: .onMyMac)
		let path = account.dataFolder + "/Subscriptions.opml"
		_ = try #require(account.ensureFolder(with: "Retry folder"))
		try FileManager.default.createDirectory(atPath: path, withIntermediateDirectories: false)
		let first = await account.closeForFixtureRemoval()
		#expect(!first)
		#expect(FileManager.default.fileExists(atPath: account.dataFolder))
		try FileManager.default.removeItem(atPath: path)
		let retried = await account.closeForFixtureRemoval()
		#expect(retried)
		let opml = try String(contentsOfFile: path, encoding: .utf8)
		#expect(opml.contains("Retry folder"))
		try await manager.deleteAccount(account)
	}

	@Test func admittedFeedCreationPersistsDownloadedArticleDuringClose() async throws {
		let manager = TestAccountManager()
		let account = manager.createAccount(type: .onMyMac)
		let path = account.dataFolder
		let folder = try #require(account.ensureFolder(with: "Existing folder"))
		account.saveIfNeeded()
		let url = "https://fixture.invalid/t30-create-feed.xml"
		let xml = """
		<?xml version="1.0"?><rss version="2.0"><channel><title>Fixture</title><link>https://fixture.invalid/</link><description>Fixture</description><item><title>Admitted article</title><guid>fixture-article</guid><link>https://fixture.invalid/article</link></item></channel></rss>
		"""
		TestingURLProtocol.$currentTestID.withValue(nil) {
			TestingURLProtocol.setResponse(.init(data: Data(xml.utf8)), forURLContaining: url)
		}
		let (downloaded, downloadedSignal) = AsyncStream<Void>.makeStream()
		let (release, releaseSignal) = AsyncStream<Void>.makeStream()
		let (closing, closingSignal) = AsyncStream<Void>.makeStream()
		account.onFixtureClosingForTesting = { closingSignal.yield(()) }
		InitialFeedDownloader.afterDownloadForTesting = {
			downloadedSignal.yield(())
			for await _ in release { break }
		}
		defer { InitialFeedDownloader.afterDownloadForTesting = nil }
		let creation = Task { @MainActor in
			await withCheckedContinuation { continuation in
				account.createFeed(url: url, name: nil, container: folder, validateFeed: true) { continuation.resume(returning: $0) }
			}
		}
		for await _ in downloaded { break }
		account.saveIfNeeded()
		let close = Task { await account.closeForFixtureRemoval() }
		for await _ in closing { break }
		account.saveIfNeeded()
		releaseSignal.yield(())
		let result = await creation.value
		_ = try result.get()
		#expect(await close.value)
		#expect(try stringValue(in: path + "/DB.sqlite3", sql: "SELECT title FROM articles WHERE title = 'Admitted article'") == "Admitted article")
		let opml = try String(contentsOfFile: path + "/Subscriptions.opml", encoding: .utf8)
		#expect(folderContents("Existing folder", in: opml).contains(url))
		try await manager.deleteAccount(account)
	}

	@Test func admittedFeedlyMoveRollbackPersistsAfterBusyClose() async throws {
		let manager = TestAccountManager()
		let account = manager.createAccount(type: .feedly)
		let from = try #require(account.ensureFolder(with: "Source"))
		let to = try #require(account.ensureFolder(with: "Destination"))
		from.externalID = "user/fixture/category/source"
		to.externalID = "user/fixture/category/destination"
		let feed = account.createFeed(with: "Fixture", url: "https://fixture.invalid/move.xml", feedID: "feed/https://fixture.invalid/move.xml", homePageURL: nil)
		from.addFeedToTreeAtTopLevel(feed)
		account.saveIfNeeded()
		let path = account.dataFolder
		let (moved, movedSignal) = AsyncStream<Void>.makeStream()
		let (release, releaseSignal) = AsyncStream<Void>.makeStream()
		let (closing, closingSignal) = AsyncStream<Void>.makeStream()
		account.onFixtureClosingForTesting = { closingSignal.yield(()) }
		FeedlyAccountDelegate.afterOptimisticMoveForTesting = {
			movedSignal.yield(())
			for await _ in release { break }
		}
		defer { FeedlyAccountDelegate.afterOptimisticMoveForTesting = nil }
		let move = Task { @MainActor in
			await withCheckedContinuation { continuation in
				account.moveFeed(feed, from: from, to: to) { continuation.resume(returning: $0) }
			}
		}
		for await _ in moved { break }
		account.saveIfNeeded()
		let optimistic = try String(contentsOfFile: path + "/Subscriptions.opml", encoding: .utf8)
		#expect(folderContents("Destination", in: optimistic).contains(feed.url))
		var destination: OpaquePointer?
		guard sqlite3_open(":memory:", &destination) == SQLITE_OK else { throw CocoaError(.fileWriteUnknown) }
		defer { sqlite3_close(destination) }
		let backup = try #require(account.feedSettingsDatabaseForTesting.withDatabaseForTesting { database in
			guard let source = database.sqliteHandle() else { return nil as OpaquePointer? }
			return sqlite3_backup_init(destination, "main", OpaquePointer(source), "main")
		})
		let close = Task { await account.closeForFixtureRemoval() }
		for await _ in closing { break }
		account.saveIfNeeded()
		releaseSignal.yield(())
		if case .success = await move.value { Issue.record("Move unexpectedly succeeded") }
		#expect(!(await close.value))
		#expect(from.topLevelFeeds.contains(feed))
		#expect(!to.topLevelFeeds.contains(feed))
		let restored = try String(contentsOfFile: path + "/Subscriptions.opml", encoding: .utf8)
		#expect(folderContents("Source", in: restored).contains(feed.url))
		#expect(!folderContents("Destination", in: restored).contains(feed.url))
		let changes = NotificationCounter()
		let observer = NotificationCenter.default.addObserver(forName: .ChildrenDidChange, object: account, queue: nil) { _ in
			changes.count.withLock { $0 += 1 }
		}
		let folderObserver = NotificationCenter.default.addObserver(forName: .ChildrenDidChange, object: from, queue: nil) { _ in
			changes.count.withLock { $0 += 1 }
		}
		from.removeFeedFromTreeAtTopLevel(feed)
		to.addFeeds([feed])
		account.removeFolderFromTree(from)
		account.folders = []
		#expect(from.topLevelFeeds.contains(feed))
		#expect(to.topLevelFeeds.isEmpty)
		#expect(account.folders?.contains(from) == true)
		#expect(changes.count.withLock { $0 } == 0)
		#expect(try String(contentsOfFile: path + "/Subscriptions.opml", encoding: .utf8) == restored)
		NotificationCenter.default.removeObserver(observer)
		NotificationCenter.default.removeObserver(folderObserver)
		let finished = sqlite3_backup_finish(backup)
		#expect(finished == SQLITE_OK)
		try await manager.deleteAccount(account)
	}

	@Test func acceptedSyncResetFinishesBeforeClose() async throws {
		let manager = TestAccountManager()
		let account = manager.createAccount(type: .feedbin)
		let delegate = try #require(account.delegate as? FeedbinAccountDelegate)
		await delegate.waitForSyncInitializationForTesting()
		let sync = delegate.syncDatabase
		let path = account.dataFolder
		await sync.insertStatuses([SyncStatus(articleID: "selected", key: .starred, flag: true)])
		#expect(try await sync.selectForProcessing().count == 1)
		let (started, startSignal) = AsyncStream<Void>.makeStream()
		let (release, releaseSignal) = AsyncStream<Void>.makeStream()
		let (closing, closingSignal) = AsyncStream<Void>.makeStream()
		account.onFixtureClosingForTesting = { closingSignal.yield(()) }
		sync.setResetHookForTesting {
			startSignal.yield(())
			for await _ in release { break }
		}
		defer { sync.setResetHookForTesting(nil) }
		let accepted = sync.resetAllSelectedForProcessing()
		#expect(accepted)
		for await _ in started { break }
		sync.beginClosing(accountID: account.accountID)
		let close = Task { await account.closeForFixtureRemoval() }
		for await _ in closing { break }
		releaseSignal.yield(())
		#expect(await close.value)
		#expect(try stringValue(in: path + "/Sync.sqlite3", sql: "SELECT selected FROM syncStatus WHERE articleID = 'selected'") == "0")
		let rejected = sync.resetAllSelectedForProcessing()
		#expect(!rejected)
		try await manager.deleteAccount(account)
	}

	@Test func retainedModelsCompleteRenameAfterAccountIsReleased() async throws {
		let manager = TestAccountManager()
		var account: Account? = manager.createAccount(type: .onMyMac)
		let feed = try #require(account?.createFeed(with: "Original", url: "https://example.com/released", feedID: "released", homePageURL: nil))
		let folder = try #require(account?.ensureFolder(with: "Original"))
		folder.externalID = "original-id"
		folder.unreadCount = 4
		try await manager.deleteAccount(try #require(account))
		account = nil
		#expect(feed.account == nil)
		#expect(folder.account == nil)
		let notifications = NotificationCounter()
		let observer = NotificationCenter.default.addObserver(forName: .DisplayNameDidChange, object: folder, queue: nil) { _ in
			notifications.count.withLock { $0 += 1 }
		}
		let childrenObserver = NotificationCenter.default.addObserver(forName: .ChildrenDidChange, object: folder, queue: nil) { _ in
			notifications.count.withLock { $0 += 1 }
		}
		let unreadObserver = NotificationCenter.default.addObserver(forName: .UnreadCountDidChange, object: folder, queue: nil) { _ in
			notifications.count.withLock { $0 += 1 }
		}
		folder.name = "Rejected"
		folder.externalID = "rejected-id"
		folder.unreadCount = 9
		#expect(folder.name == "Original")
		#expect(folder.externalID == "original-id" && folder.unreadCount == 4)
		folder.addFeedToTreeAtTopLevel(feed)
		folder.topLevelFeeds = [feed]
		folder.folders = [folder]
		#expect(folder.topLevelFeeds.isEmpty)
		#expect(folder.folders == nil)
		#expect(notifications.count.withLock { $0 } == 0)
		NotificationCenter.default.removeObserver(observer)
		NotificationCenter.default.removeObserver(childrenObserver)
		NotificationCenter.default.removeObserver(unreadObserver)
		let feedResult: Result<Void, Error> = await withCheckedContinuation { continuation in
			feed.rename(to: "Rejected") { continuation.resume(returning: $0) }
		}
		let folderResult: Result<Void, Error> = await withCheckedContinuation { continuation in
			folder.rename(to: "Rejected") { continuation.resume(returning: $0) }
		}
		if case .failure(let error) = feedResult { #expect(error is CancellationError) } else { Issue.record("Feed rename unexpectedly succeeded") }
		if case .failure(let error) = folderResult { #expect(error is CancellationError) } else { Issue.record("Folder rename unexpectedly succeeded") }
	}

	@Test func admissionStopsDuringCloseWhileAcceptedWorkFinishes() async throws {
		let manager = TestAccountManager()
		let account = manager.createAccount(type: .onMyMac)
		let feed = account.createFeed(with: "Original", url: "https://example.com/during", feedID: "during", homePageURL: nil)
		let folder = try #require(account.ensureFolder(with: "Before"))
		folder.externalID = "initial-id"
		folder.unreadCount = 3
		let detachedFolder = Folder(account: account, name: "Detached")
		let other = account.createFeed(with: "Other", url: "https://example.com/other", feedID: "other", homePageURL: nil)
		account.addFeedToTreeAtTopLevel(feed)
		account.saveIfNeeded()
		let path = account.dataFolder
		let (started, startSignal) = AsyncStream<Void>.makeStream()
		let (release, releaseSignal) = AsyncStream<Void>.makeStream()
		let (closing, closingSignal) = AsyncStream<Void>.makeStream()
		account.onFixtureClosingForTesting = { closingSignal.yield(()) }
		account.startBackground {
			feed.editedName = "Before"
			startSignal.yield(())
			for await _ in release { break }
			feed.editedName = "Admitted"
			folder.externalID = "admitted-id"
			folder.addFeedToTreeAtTopLevel(other)
			let changed = await account.database.markAndFetchNewAsync(articleIDs: ["admitted"], statusKey: .starred, flag: true)
			#expect(changed == ["admitted"])
			folder.unreadCount = 7
		}
		for await _ in started { break }
		let close = Task { await account.closeForFixtureRemoval() }
		for await _ in closing { break }
		let children = NotificationCounter()
		let childrenObserver = NotificationCenter.default.addObserver(forName: .ChildrenDidChange, object: account, queue: nil) { _ in
			children.count.withLock { $0 += 1 }
		}
		let folderChildrenObserver = NotificationCenter.default.addObserver(forName: .ChildrenDidChange, object: folder, queue: nil) { _ in
			children.count.withLock { $0 += 1 }
		}
		let originalOPML = try String(contentsOfFile: path + "/Subscriptions.opml", encoding: .utf8)
		account.removeFeedFromTreeAtTopLevel(feed)
		account.removeFeedsFromTreeAtTopLevel([feed])
		account.removeAllInstancesOfFeedFromTreeAtAllLevels(feed)
		account.addFeedToTreeAtTopLevel(other)
		account.removeFolderFromTree(folder)
		account.addFolderToTree(detachedFolder)
		account.addFeedIfNotInAnyFolder(other)
		#expect(account.ensureFolder(withFolderNames: ["Rejected"]) == nil)
		account.topLevelFeeds = []
		account.folders = []
		folder.addFeedToTreeAtTopLevel(other)
		folder.addFeeds([other])
		folder.removeFeedFromTreeAtTopLevel(other)
		folder.removeFeedsFromTreeAtTopLevel([other])
		folder.replaceTopLevelFeeds([other])
		folder.topLevelFeeds = [other]
		folder.folders = [folder]
		account.postChildrenDidChangeNotification()
		folder.postChildrenDidChangeNotification()
		#expect(account.topLevelFeeds == [feed])
		#expect(account.folders == [folder])
		#expect(folder.topLevelFeeds.isEmpty)
		#expect(folder.folders == nil)
		#expect(children.count.withLock { $0 } == 0)
		#expect(try String(contentsOfFile: path + "/Subscriptions.opml", encoding: .utf8) == originalOPML)
		NotificationCenter.default.removeObserver(childrenObserver)
		NotificationCenter.default.removeObserver(folderChildrenObserver)
		let notifications = NotificationCounter()
		let observer = NotificationCenter.default.addObserver(forName: .feedSettingDidChange, object: feed, queue: nil) { _ in
			notifications.count.withLock { $0 += 1 }
		}
		let displayObserver = NotificationCenter.default.addObserver(forName: .DisplayNameDidChange, object: feed, queue: nil) { _ in
			notifications.count.withLock { $0 += 1 }
		}
		let folderObserver = NotificationCenter.default.addObserver(forName: .DisplayNameDidChange, object: folder, queue: nil) { _ in
			notifications.count.withLock { $0 += 1 }
		}
		let unreadObserver = NotificationCenter.default.addObserver(forName: .UnreadCountDidChange, object: folder, queue: nil) { _ in
			notifications.count.withLock { $0 += 1 }
		}
		feed.editedName = "Rejected"
		folder.name = "Rejected"
		folder.externalID = "rejected-id"
		folder.unreadCount = 99
		#expect(folder.name == "Before")
		#expect(folder.externalID == "initial-id" && folder.unreadCount == 3)
		#expect(feed.editedName == "Before")
		#expect(notifications.count.withLock { $0 } == 0)
		NotificationCenter.default.removeObserver(observer)
		NotificationCenter.default.removeObserver(displayObserver)
		NotificationCenter.default.removeObserver(folderObserver)
		NotificationCenter.default.removeObserver(unreadObserver)
		#expect(await account.fetchArticlesAsync(.feed(feed)).isEmpty)
		let rejected = await account.database.markAndFetchNewAsync(articleIDs: ["rejected"], statusKey: .starred, flag: true)
		#expect(rejected.isEmpty)
		let created = await account.database.createStatusesIfNeededAsync(articleIDs: ["rejected"])
		let deleted = await account.database.deleteAsync(articleIDs: ["admitted"])
		#expect(!created && !deleted)
		#expect(FileManager.default.fileExists(atPath: path))
		releaseSignal.yield(())
		let closed = await close.value
		#expect(closed)
		#expect(folder.topLevelFeeds == [other])
		#expect(folder.externalID == "admitted-id" && folder.unreadCount == 7)
		let finalOPML = try String(contentsOfFile: path + "/Subscriptions.opml", encoding: .utf8)
		#expect(finalOPML.contains("admitted-id"))
		#expect(folderContents("Before", in: finalOPML).contains(other.url))
		let closedChildren = NotificationCounter()
		let closedObserver = NotificationCenter.default.addObserver(forName: .ChildrenDidChange, object: account, queue: nil) { _ in
			closedChildren.count.withLock { $0 += 1 }
		}
		let closedFolderObserver = NotificationCenter.default.addObserver(forName: .ChildrenDidChange, object: folder, queue: nil) { _ in
			closedChildren.count.withLock { $0 += 1 }
		}
		folder.replaceTopLevelFeeds([])
		account.removeAllInstancesOfFeedFromTreeAtAllLevels(other)
		account.topLevelFeeds = []
		account.folders = []
		#expect(folder.topLevelFeeds == [other])
		#expect(account.topLevelFeeds == [feed])
		#expect(account.folders == [folder])
		#expect(closedChildren.count.withLock { $0 } == 0)
		#expect(try String(contentsOfFile: path + "/Subscriptions.opml", encoding: .utf8) == finalOPML)
		NotificationCenter.default.removeObserver(closedObserver)
		NotificationCenter.default.removeObserver(closedFolderObserver)
		let afterCloseNotifications = NotificationCounter()
		let afterCloseObserver = NotificationCenter.default.addObserver(forName: .DisplayNameDidChange, object: folder, queue: nil) { _ in
			afterCloseNotifications.count.withLock { $0 += 1 }
		}
		let afterCloseUnreadObserver = NotificationCenter.default.addObserver(forName: .UnreadCountDidChange, object: folder, queue: nil) { _ in
			afterCloseNotifications.count.withLock { $0 += 1 }
		}
		folder.name = "Rejected after close"
		folder.externalID = "rejected-after-close"
		folder.unreadCount = 99
		#expect(folder.name == "Before")
		#expect(folder.externalID == "admitted-id" && folder.unreadCount == 7)
		#expect(afterCloseNotifications.count.withLock { $0 } == 0)
		NotificationCenter.default.removeObserver(afterCloseObserver)
		NotificationCenter.default.removeObserver(afterCloseUnreadObserver)
		#expect(feed.editedName == "Admitted")
		#expect(try stringValue(in: path + "/FeedSettings.db", sql: "SELECT editedName FROM feedSettings WHERE feedID = 'during'") == "Admitted")
		#expect(try stringValue(in: path + "/DB.sqlite3", sql: "SELECT starred FROM statuses WHERE articleID = 'admitted'") == "1")
		#expect(try stringValue(in: path + "/DB.sqlite3", sql: "SELECT starred FROM statuses WHERE articleID = 'rejected'") == nil)
		try await manager.deleteAccount(account)
		#expect(!FileManager.default.fileExists(atPath: path))
	}

	@Test func failedAccountCloseCanBeRetried() async throws {
		let manager = TestAccountManager()
		let account = manager.createAccount(type: .feedbin)
		let path = account.dataFolder
		_ = try #require(account.ensureFolder(with: "Persisted folder"))
		let feed = account.createFeed(with: "Original", url: "https://example.com/fixture", feedID: "fixture-feed", homePageURL: nil)
		feed.editedName = "Accepted"
		let sync = try #require(account.delegate as? FeedbinAccountDelegate).syncDatabase
		let settingsIdentity = try identity(path + "/FeedSettings.db")
		var destination: OpaquePointer?
		guard sqlite3_open(":memory:", &destination) == SQLITE_OK else { throw CocoaError(.fileWriteUnknown) }
		defer { sqlite3_close(destination) }
		let backup = try #require(account.feedSettingsDatabaseForTesting.withDatabaseForTesting { database in
			guard let source = database.sqliteHandle() else { return nil as OpaquePointer? }
			return sqlite3_backup_init(destination, "main", OpaquePointer(source), "main")
		})
		async let first = account.closeForFixtureRemoval()
		async let second = account.closeForFixtureRemoval()
		let results = await (first, second)
		#expect(!results.0 && !results.1)
		let opml = try String(contentsOfFile: path + "/Subscriptions.opml", encoding: .utf8)
		#expect(opml.contains("Persisted folder"))
		#expect(FileManager.default.fileExists(atPath: path))
		#expect(hasOpenFile(settingsIdentity))
		feed.editedName = "Rejected"
		#expect(feed.editedName == "Accepted")
		let settingsWrite = account.feedSettingsDatabaseForTesting.setString("Rejected", for: feed.url, column: .editedName)
		#expect(!settingsWrite)
		#expect(await account.fetchArticlesAsync(.feed(feed)).isEmpty)
		await #expect(throws: CancellationError.self) {
			try await sync.selectPendingCount()
		}
		let inserted = await sync.insertStatuses([SyncStatus(articleID: "rejected", key: .starred, flag: true)])
		#expect(!inserted)
		#expect(try stringValue(in: path + "/FeedSettings.db", sql: "SELECT editedName FROM feedSettings WHERE feedID = 'fixture-feed'") == "Accepted")
		let finishResult = sqlite3_backup_finish(backup)
		#expect(finishResult == SQLITE_OK)
		try await manager.deleteAccount(account)
		#expect(!FileManager.default.fileExists(atPath: path))
		#expect(!hasOpenFile(settingsIdentity))
	}

	@Test func throwingBodyStillRemovesItsFixture() async throws {
		let manager = TestAccountManager()
		var path = ""
		await #expect(throws: FixtureError.expected) {
			try await manager.withAccount(type: .feedbin) { account in
				path = account.dataFolder
				throw FixtureError.expected
			}
		}
		#expect(!path.isEmpty)
		#expect(!FileManager.default.fileExists(atPath: path))
	}

	@Test func removalClosesTheOriginalDatabaseFiles() async throws {
		let manager = TestAccountManager()
		let account = manager.createAccount(type: .feedbin)
		let identities = try ["DB.sqlite3", "Sync.sqlite3", "FeedSettings.db"].map {
			try identity(account.dataFolder + "/" + $0)
		}
		for file in identities { #expect(hasOpenFile(file)) }
		try await manager.deleteAccount(account)
		for file in identities { #expect(!hasOpenFile(file)) }
	}

	@Test func retainedFeedRejectsChangesAfterClose() async throws {
		let manager = TestAccountManager()
		try await manager.withAccount(type: .onMyMac) { account in
			let feed = account.createFeed(with: "Original", url: "https://example.com/feed", feedID: "fixture", homePageURL: nil)
			let files = try ["DB.sqlite3", "FeedSettings.db"].map { try identity(account.dataFolder + "/" + $0) }
			feed.editedName = "Before close"
			let closed = await account.closeForFixtureRemoval()
			#expect(closed)
			feed.editedName = "After close"
			#expect(feed.editedName == "Before close")
			let articles = await account.fetchArticlesAsync(.feed(feed))
			#expect(articles.isEmpty)
			for file in files { #expect(!hasOpenFile(file)) }
			#expect(try stringValue(in: account.dataFolder + "/FeedSettings.db", sql: "SELECT editedName FROM feedSettings WHERE feedID = 'fixture'") == "Before close")
		}
	}

	@Test func closesDatabasesBeforeRemovingOnlyOwnedDirectory() async throws {
		TestingURLProtocol.setResponse("tags.json", file: "JSON/tags_add.json")
		TestingURLProtocol.setResponse("subscriptions.json", file: "JSON/subscriptions_initial.json")
		let manager = TestAccountManager()
		try await manager.withAccount(type: .feedbin) { other in
			let otherPath = other.dataFolder
			let foreignManager = TestAccountManager()
			await #expect(throws: (any Error).self) {
				try await foreignManager.deleteAccount(other)
			}
			#expect(FileManager.default.fileExists(atPath: otherPath))
			var removedPath = ""
			try await manager.withAccount(type: .feedbin) { account in
				removedPath = account.dataFolder
				try await account.refreshAll()
				let feed = try #require(account.idToFeedDictionary["1296379"])
				feed.editedName = "Lifetime fixture"
				let sync = try #require(account.delegate as? FeedbinAccountDelegate).syncDatabase
				await sync.insertStatuses([SyncStatus(articleID: "fixture", key: .starred, flag: true)])
				#expect(try await sync.selectPendingStarredStatusArticleIDs().contains("fixture"))
				let files = ["DB.sqlite3", "Sync.sqlite3", "FeedSettings.db"].map { account.dataFolder + "/" + $0 }
				for file in files { #expect(isOpen(file)) }
				let closed = await account.closeForFixtureRemoval()
				#expect(closed)
				#expect(FileManager.default.fileExists(atPath: account.dataFolder))
				for file in files { #expect(!isOpen(file)) }
				#expect(try stringValue(in: files[2], sql: "SELECT editedName FROM feedSettings WHERE feedID = '1296379'") == "Lifetime fixture")
				#expect(try stringValue(in: files[1], sql: "SELECT articleID FROM syncStatus WHERE articleID = 'fixture'") == "fixture")
			}
			#expect(!FileManager.default.fileExists(atPath: removedPath))
			#expect(FileManager.default.fileExists(atPath: otherPath))
		}
	}

	private func isOpen(_ path: String) -> Bool {
		let expected = URL(fileURLWithPath: path).resolvingSymlinksInPath().path
		for descriptor in 0..<getdtablesize() {
			var buffer = [CChar](repeating: 0, count: Int(MAXPATHLEN))
			if fcntl(descriptor, F_GETPATH, &buffer) == 0 {
				let name = String(decoding: buffer.prefix { $0 != 0 }.map { UInt8(bitPattern: $0) }, as: UTF8.self)
				if URL(fileURLWithPath: name).resolvingSymlinksInPath().path == expected {
					return true
				}
			}
		}
		return false
	}

	private func folderContents(_ name: String, in opml: String) -> String {
		guard let start = opml.range(of: "<outline text=\"\(name)\"") else { return "" }
		let rest = opml[start.lowerBound...]
		let firstLine = String(rest.prefix { $0 != "\n" })
		if firstLine.hasSuffix("/>") { return firstLine }
		guard let end = rest.range(of: "</outline>") else { return String(rest.prefix { $0 != "\n" }) }
		return String(rest[..<end.upperBound])
	}

	private func identity(_ path: String) throws -> (dev_t, ino_t) {
		var info = stat()
		guard lstat(path, &info) == 0 else { throw CocoaError(.fileReadNoSuchFile) }
		return (info.st_dev, info.st_ino)
	}

	private func hasOpenFile(_ identity: (dev_t, ino_t)) -> Bool {
		for descriptor in 0..<getdtablesize() {
			var info = stat()
			if fstat(descriptor, &info) == 0 && info.st_dev == identity.0 && info.st_ino == identity.1 {
				return true
			}
		}
		return false
	}

	private func stringValue(in path: String, sql: String) throws -> String? {
		var database: OpaquePointer?
		guard sqlite3_open_v2(path, &database, SQLITE_OPEN_READONLY, nil) == SQLITE_OK else {
			throw CocoaError(.fileReadUnknown)
		}
		defer { sqlite3_close(database) }
		var statement: OpaquePointer?
		guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
			throw CocoaError(.fileReadUnknown)
		}
		defer { sqlite3_finalize(statement) }
		guard sqlite3_step(statement) == SQLITE_ROW, let value = sqlite3_column_text(statement, 0) else { return nil }
		return String(cString: value)
	}
}
