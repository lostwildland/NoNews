import Foundation
import Testing
import Articles
@testable import Account
@testable import NetNewsWire

@MainActor @Suite struct MarkStatusCommandTests {
	private final class UnrelatedAction: NSObject {
		var called = false
	}

	@Test func failedMarkDoesNotCreateUndoOrRemoveUnrelatedHistory() async throws {
		let undo = UndoManager()
		let unrelated = UnrelatedAction()
		undo.beginUndoGrouping()
		undo.registerUndo(withTarget: unrelated) { $0.called = true }
		undo.setActionName("Unrelated")
		undo.endUndoGrouping()
		let status = ArticleStatus(articleID: "missing", read: false, starred: false, dateArrived: Date())
		let article = Article(accountID: "missing-fixture-\(UUID().uuidString)", articleID: "missing", feedID: "fixture", uniqueID: "missing", title: nil, contentHTML: nil, contentText: nil, markdown: nil, url: nil, externalURL: nil, summary: nil, imageURL: nil, datePublished: nil, dateModified: nil, authors: nil, status: status)
		let (finished, signal) = AsyncStream<Void>.makeStream()
		let command = try #require(MarkStatusCommand(initialArticles: [article], markingRead: true, undoManager: undo, completion: { signal.yield(()) }))
		command.perform()
		for await _ in finished { break }
		#expect(undo.undoActionName == "Unrelated")
		undo.undo()
		#expect(unrelated.called)
	}
	@Test func partialMarkUndoRedoAndRejectedUndoPreserveOtherHistory() async throws {
		let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
		let firstPath = root.appendingPathComponent("first", isDirectory: true)
		let secondPath = root.appendingPathComponent("second", isDirectory: true)
		try FileManager.default.createDirectory(at: firstPath, withIntermediateDirectories: true)
		try FileManager.default.createDirectory(at: secondPath, withIntermediateDirectories: true)
		let first = Account(dataFolder: firstPath.path, type: .onMyMac, accountID: UUID().uuidString)
		let second = Account(dataFolder: secondPath.path, type: .onMyMac, accountID: UUID().uuidString)
		await first.waitForFixtureBackgroundWorkForTesting()
		await second.waitForFixtureBackgroundWorkForTesting()
		await first.createStatusesIfNeededAsync(articleIDs: ["first"])
		try await first.markArticles(articleIDs: ["first"], statusKey: .read, flag: false)
		#expect(await second.closeForFixtureRemoval())
		func article(_ id: String, _ accountID: String) -> Article {
			let status = ArticleStatus(articleID: id, read: false, starred: false, dateArrived: Date())
			return Article(accountID: accountID, articleID: id, feedID: "fixture", uniqueID: id, title: nil, contentHTML: nil, contentText: nil, markdown: nil, url: nil, externalURL: nil, summary: nil, imageURL: nil, datePublished: nil, dateModified: nil, authors: nil, status: status)
		}
		let undo = UndoManager()
		undo.groupsByEvent = false
		let unrelated = UnrelatedAction()
		undo.beginUndoGrouping()
		undo.registerUndo(withTarget: unrelated) { $0.called = true }
		undo.setActionName("Unrelated")
		undo.endUndoGrouping()
		let command = try #require(MarkStatusCommand(initialArticles: [article("first", first.accountID), article("second", second.accountID)], markingRead: true, undoManager: undo))
		command.accountResolverForTesting = { id in id == first.accountID ? first : (id == second.accountID ? second : nil) }
		let (finished, signal) = AsyncStream<Void>.makeStream()
		var outcomes = [ArticleMarkResult]()
		command.onMarkFinishedForTesting = { outcomes.append($0); signal.yield(()) }
		var iterator = finished.makeAsyncIterator()
		undo.beginUndoGrouping()
		command.perform()
		_ = await iterator.next()
		undo.endUndoGrouping()
		#expect(outcomes[0].succeeded[first.accountID] == ["first"] && outcomes[0].failed[second.accountID] != nil)
		#expect(!(try await first.fetchUnreadArticleIDsAsync()).contains("first"))
		undo.undo()
		_ = await iterator.next()
		#expect(try await first.fetchUnreadArticleIDsAsync().contains("first"))
		#expect(undo.canRedo)
		undo.redo()
		_ = await iterator.next()
		#expect(!(try await first.fetchUnreadArticleIDsAsync()).contains("first"))
		#expect(await first.closeForFixtureRemoval())
		undo.undo()
		_ = await iterator.next()
		#expect(outcomes.last?.succeeded.isEmpty == true && undo.canRedo == false)
		#expect(undo.undoActionName == "Unrelated")
		undo.undo()
		#expect(unrelated.called)
		first.deleteSettings()
		second.deleteSettings()
		try FileManager.default.removeItem(at: root)
	}

	@Test func rejectedRedoDoesNotCreateUndoOrRemoveOtherHistory() async throws {
		let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
		try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
		let account = Account(dataFolder: root.path, type: .onMyMac, accountID: UUID().uuidString)
		await account.waitForFixtureBackgroundWorkForTesting()
		await account.createStatusesIfNeededAsync(articleIDs: ["fixture"])
		try await account.markArticles(articleIDs: ["fixture"], statusKey: .read, flag: false)
		let status = ArticleStatus(articleID: "fixture", read: false, starred: false, dateArrived: Date())
		let article = Article(accountID: account.accountID, articleID: "fixture", feedID: "fixture", uniqueID: "fixture", title: nil, contentHTML: nil, contentText: nil, markdown: nil, url: nil, externalURL: nil, summary: nil, imageURL: nil, datePublished: nil, dateModified: nil, authors: nil, status: status)
		let undo = UndoManager()
		undo.groupsByEvent = false
		let unrelated = UnrelatedAction()
		undo.beginUndoGrouping()
		undo.registerUndo(withTarget: unrelated) { $0.called = true }
		undo.setActionName("Unrelated")
		undo.endUndoGrouping()
		let command = try #require(MarkStatusCommand(initialArticles: [article], markingRead: true, undoManager: undo))
		command.accountResolverForTesting = { _ in account }
		let (finished, signal) = AsyncStream<Void>.makeStream()
		var outcomes = [ArticleMarkResult]()
		command.onMarkFinishedForTesting = { outcomes.append($0); signal.yield(()) }
		var iterator = finished.makeAsyncIterator()
		undo.beginUndoGrouping()
		command.perform()
		_ = await iterator.next()
		undo.endUndoGrouping()
		undo.undo()
		_ = await iterator.next()
		#expect(try await account.fetchUnreadArticleIDsAsync().contains("fixture"))
		#expect(await account.closeForFixtureRemoval())
		undo.redo()
		_ = await iterator.next()
		#expect(outcomes.last?.succeeded.isEmpty == true && undo.undoActionName == "Unrelated")
		undo.undo()
		#expect(unrelated.called)
		account.deleteSettings()
		try FileManager.default.removeItem(at: root)
	}

}
