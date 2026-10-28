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

	private struct GatedFetcher: ArticleFetcher {
		let started: AsyncStream<Void>.Continuation
		let release: AsyncStream<Void>
		func fetchArticles() throws -> Set<Article> { [] }
		func fetchUnreadArticles() throws -> Set<Article> { [] }
		func fetchArticlesAsync() async throws -> Set<Article> {
			started.yield(())
			for await _ in release { break }
			return []
		}
		func fetchUnreadArticlesAsync() async throws -> Set<Article> { try await fetchArticlesAsync() }
	}

	@Test func cancellingRunningAndPendingRequestsDoesNotPublishStaleResults() async {
		let (started, startedSignal) = AsyncStream<Void>.makeStream()
		let (release, releaseSignal) = AsyncStream<Void>.makeStream()
		let (finished, finishedSignal) = AsyncStream<Void>.makeStream()
		let queue = FetchRequestQueue()
		var outcomes = [Int: Int]()
		let first = FetchRequestOperation(id: 1, readFilterEnabledTable: [:], fetchers: [GatedFetcher(started: startedSignal, release: release)]) { result, operation in
			outcomes[operation.id, default: 0] += 1
			if case .failure(let error) = result { #expect(error is CancellationError) }
			else { Issue.record("Cancelled running request published a result") }
		}
		let second = FetchRequestOperation(id: 2, readFilterEnabledTable: [:], fetchers: [Fetcher(shouldFail: false)]) { result, operation in
			outcomes[operation.id, default: 0] += 1
			if case .failure(let error) = result { #expect(error is CancellationError) }
			else { Issue.record("Cancelled pending request published a result") }
		}
		queue.add(first)
		for await _ in started { break }
		queue.add(second)
		queue.cancelAllRequests()
		let latest = FetchRequestOperation(id: 3, readFilterEnabledTable: [:], fetchers: [Fetcher(shouldFail: false)]) { result, operation in
			outcomes[operation.id, default: 0] += 1
			if case .success(let articles) = result { #expect(articles.isEmpty) }
			else { Issue.record("Latest request failed") }
			finishedSignal.yield(())
		}
		queue.add(latest)
		releaseSignal.finish()
		for await _ in finished { break }
		#expect(outcomes == [1: 1, 2: 1, 3: 1])
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
