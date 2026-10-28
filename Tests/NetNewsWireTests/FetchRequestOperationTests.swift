import Foundation
import Testing
import Account
import Articles
@testable import NetNewsWire

@MainActor @Suite struct FetchRequestOperationTests {
	private struct Fetcher: ArticleFetcher {
		let shouldFail: Bool
		func fetchArticles() throws -> Set<Article> {
			if shouldFail { throw CancellationError() }
			return []
		}
		func fetchUnreadArticles() throws -> Set<Article> { try fetchArticles() }
		func fetchArticlesAsync() async throws -> Set<Article> { try fetchArticles() }
		func fetchUnreadArticlesAsync() async throws -> Set<Article> { try fetchArticles() }
	}

	@Test(arguments: [false, true]) func completesResultForEmptyAndRejectedFetch(shouldFail: Bool) async {
		var callbacks = 0
		let operation = FetchRequestOperation(id: 1, readFilterEnabledTable: [:], fetchers: [Fetcher(shouldFail: shouldFail)]) { result, _ in
			callbacks += 1
			if shouldFail {
				if case .failure(let error) = result { #expect(error is CancellationError) }
				else { Issue.record("Rejected fetch returned success") }
			} else {
				if case .success(let articles) = result { #expect(articles.isEmpty) }
				else { Issue.record("Empty fetch failed") }
			}
		}
		await withCheckedContinuation { continuation in
			operation.run { _ in continuation.resume() }
		}
		operation.cancel()
		#expect(callbacks == 1)
	}

	@Test func cancellingPendingOperationCompletesOnce() {
		var callbacks = 0
		let operation = FetchRequestOperation(id: 2, readFilterEnabledTable: [:], fetchers: [Fetcher(shouldFail: false)]) { result, _ in
			callbacks += 1
			if case .failure(let error) = result { #expect(error is CancellationError) }
			else { Issue.record("Cancelled request returned success") }
		}
		operation.cancel()
		operation.cancel()
		#expect(callbacks == 1)
	}
}
